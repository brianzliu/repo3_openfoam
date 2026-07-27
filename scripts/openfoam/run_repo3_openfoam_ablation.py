#!/usr/bin/env python3
"""Run GEOS-style R/S/X/M ablations for the repo3_openfoam benchmark path."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugin"
DEFAULT_TASKS_ROOT = (
    REPO_ROOT / "data" / "openfoam_benchmark" / "foamgpt_subset_seed42" / "tasks"
)
DEFAULT_RESULTS_ROOT = REPO_ROOT / "data" / "openfoam_runs" / "repo3_openfoam_ablations"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_API_BASE = "https://openrouter.ai/api"
DEFAULT_VECTOR_DB_DIR = REPO_ROOT / "data" / "openfoam_benchmark" / "chromadb_openfoam"
RUNTIME_PLUGIN_ROOT = REPO_ROOT / "data" / "openfoam_runs" / "_runtime_openfoam_plugins"

# OpenRouter effective pricing for deepseek/deepseek-v4-flash (2026-05-30):
# https://openrouter.ai/deepseek/deepseek-v4-flash
OPENROUTER_INPUT_PRICE_PER_M = 0.0983
OPENROUTER_OUTPUT_PRICE_PER_M = 0.1966
PRICE_SOURCE = (
    "OpenRouter effective pricing 2026-05-30: "
    f"input ${OPENROUTER_INPUT_PRICE_PER_M}/M, output ${OPENROUTER_OUTPUT_PRICE_PER_M}/M"
)


def estimate_openrouter_cost(prompt_tokens: float, completion_tokens: float) -> float:
    return round(
        prompt_tokens / 1_000_000 * OPENROUTER_INPUT_PRICE_PER_M
        + completion_tokens / 1_000_000 * OPENROUTER_OUTPUT_PRICE_PER_M,
        6,
    )


CELL_ORDER = [
    "vanilla",
    "r+m",
    "s+m",
    "r+s",
    "x+m",
    "r+x",
    "s+x",
    "r+s+x+m",
    "s+x+m",
]


@dataclass(frozen=True)
class CellConfig:
    r: bool
    s: bool
    x: bool
    m: bool


CELLS: dict[str, CellConfig] = {
    "vanilla": CellConfig(False, False, False, False),
    "r+m": CellConfig(True, False, False, True),
    "s+m": CellConfig(False, True, False, True),
    "r+s": CellConfig(True, True, False, False),
    "x+m": CellConfig(False, False, True, True),
    "r+x": CellConfig(True, False, True, False),
    "s+x": CellConfig(False, True, True, False),
    "r+s+x+m": CellConfig(True, True, True, True),
    "s+x+m": CellConfig(False, True, True, True),
}


def task_dirs(tasks_root: Path, include: list[str] | None) -> list[Path]:
    tasks = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if include:
        names = set(include)
        tasks = [task for task in tasks if task.name in names]
    return tasks


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_stream_json_tool_metrics(stdout_text: str) -> dict[str, object]:
    tool_counts: dict[str, int] = {}
    assistant_messages = 0
    parse_errors = 0

    def walk(value: object) -> None:
        nonlocal assistant_messages
        if isinstance(value, dict):
            block_type = value.get("type")
            if block_type == "assistant":
                assistant_messages += 1
            if block_type == "tool_use":
                name = value.get("name") or value.get("tool_name") or "unknown"
                tool_counts[name] = tool_counts.get(name, 0) + 1
            if "tool_name" in value and value.get("event") in {"tool_run_ok", "tool_run_error"}:
                name = str(value.get("tool_name"))
                tool_counts[name] = tool_counts.get(name, 0) + 1
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        walk(payload)

    mcp_calls = sum(count for name, count in tool_counts.items() if name.startswith("mcp__"))
    metrics = {
        "tool_count_definition": "claude_stream_json_tool_use_blocks",
        "tool_calls": sum(tool_counts.values()),
        "assistant_messages": assistant_messages,
        "mcp_calls": mcp_calls,
        "tool_counts_by_name": tool_counts,
        "stream_json_parse_errors": parse_errors,
    }
    for tool_name in ("Read", "Grep", "Glob", "Write", "Edit", "Bash"):
        metrics[f"{tool_name.lower()}_calls"] = tool_counts.get(tool_name, 0)
    return metrics


def parse_stream_json_token_usage(stdout_text: str, model: str) -> dict[str, object]:
    """Extract real token usage from the Claude Code stream-json ``result`` event.

    Per-assistant-message ``usage`` blocks are zeroed for OpenRouter-routed
    models, but the terminal ``result`` event carries the true totals in
    ``usage`` plus a per-model breakdown in ``modelUsage``. We separate the
    benchmark agent model (deepseek) from Claude Code's internal helper model
    (haiku, used for quota/titling) so token/cost figures are apples-to-apples
    with Foam Agent and MetaOpenFOAM, which only call the agent model.
    """
    result_event: dict | None = None
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line or '"type":"result"' not in line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("type") == "result":
            result_event = payload  # keep the last result event

    metrics: dict[str, object] = {
        "token_usage_found": result_event is not None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "agent_model_input_tokens": 0,
        "agent_model_output_tokens": 0,
        "agent_model_total_tokens": 0,
        "helper_model_input_tokens": 0,
        "helper_model_output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    if result_event is None:
        return metrics

    model_usage = result_event.get("modelUsage")
    if isinstance(model_usage, dict) and model_usage:
        for name, usage in model_usage.items():
            if not isinstance(usage, dict):
                continue
            in_tok = int(usage.get("inputTokens", 0) or 0)
            out_tok = int(usage.get("outputTokens", 0) or 0)
            is_helper = "claude" in name.lower() or "haiku" in name.lower()
            if is_helper:
                metrics["helper_model_input_tokens"] += in_tok
                metrics["helper_model_output_tokens"] += out_tok
            else:
                metrics["agent_model_input_tokens"] += in_tok
                metrics["agent_model_output_tokens"] += out_tok
                metrics["cache_read_input_tokens"] += int(usage.get("cacheReadInputTokens", 0) or 0)
                metrics["cache_creation_input_tokens"] += int(usage.get("cacheCreationInputTokens", 0) or 0)
        metrics["agent_model_total_tokens"] = (
            metrics["agent_model_input_tokens"] + metrics["agent_model_output_tokens"]
        )
    else:
        # Fall back to the top-level usage block (this is the main agent model).
        usage = result_event.get("usage") or {}
        metrics["agent_model_input_tokens"] = int(usage.get("input_tokens", 0) or 0)
        metrics["agent_model_output_tokens"] = int(usage.get("output_tokens", 0) or 0)
        metrics["agent_model_total_tokens"] = (
            metrics["agent_model_input_tokens"] + metrics["agent_model_output_tokens"]
        )
        metrics["cache_read_input_tokens"] = int(usage.get("cache_read_input_tokens", 0) or 0)
        metrics["cache_creation_input_tokens"] = int(usage.get("cache_creation_input_tokens", 0) or 0)

    # Primary input/output/total = agent model (deepseek) for cross-agent parity.
    metrics["input_tokens"] = metrics["agent_model_input_tokens"]
    metrics["output_tokens"] = metrics["agent_model_output_tokens"]
    metrics["total_tokens"] = metrics["agent_model_total_tokens"]
    metrics["estimated_openrouter_cost_usd"] = estimate_openrouter_cost(
        float(metrics["agent_model_input_tokens"]),
        float(metrics["agent_model_output_tokens"]),
    )
    metrics["cost_price_source"] = PRICE_SOURCE
    # Claude Code's own total_cost_usd is computed with Anthropic pricing applied
    # to OpenRouter-routed tokens, so it is NOT real billing; keep it labeled.
    if "total_cost_usd" in result_event:
        metrics["claude_reported_cost_usd_not_billing"] = result_event.get("total_cost_usd")
    return metrics


def aggregate_efficiency(results: list[dict[str, object]]) -> dict[str, object]:
    completed = [result for result in results if "elapsed_seconds" in result]
    if not completed:
        return {}

    def mean_for(key: str) -> float:
        values = [float(result.get(key, 0)) for result in completed]
        return round(sum(values) / len(values), 4)

    total_input = sum(float(result.get("input_tokens", 0) or 0) for result in completed)
    total_output = sum(float(result.get("output_tokens", 0) or 0) for result in completed)
    total_tokens = sum(float(result.get("total_tokens", 0) or 0) for result in completed)
    n_with_tokens = sum(1 for result in completed if result.get("token_usage_found"))

    return {
        "tool_count_definition": "claude_stream_json_tool_use_blocks",
        "n_tasks": len(completed),
        "mean_wall_seconds": mean_for("elapsed_seconds"),
        "mean_tools_per_task": mean_for("tool_calls"),
        "mean_mcp_calls_per_task": mean_for("mcp_calls"),
        "mean_assistant_messages_per_task": mean_for("assistant_messages"),
        "mean_read_calls_per_task": mean_for("read_calls"),
        "mean_grep_calls_per_task": mean_for("grep_calls"),
        "mean_glob_calls_per_task": mean_for("glob_calls"),
        "mean_write_calls_per_task": mean_for("write_calls"),
        "mean_edit_calls_per_task": mean_for("edit_calls"),
        "mean_bash_calls_per_task": mean_for("bash_calls"),
        "tokens_definition": "agent_model_only_deepseek_from_stream_json_result_event",
        "n_tasks_with_token_usage": n_with_tokens,
        "mean_input_tokens_per_task": mean_for("input_tokens"),
        "mean_output_tokens_per_task": mean_for("output_tokens"),
        "mean_total_tokens_per_task": mean_for("total_tokens"),
        "mean_helper_model_input_tokens_per_task": mean_for("helper_model_input_tokens"),
        "mean_helper_model_output_tokens_per_task": mean_for("helper_model_output_tokens"),
        "total_input_tokens": int(total_input),
        "total_output_tokens": int(total_output),
        "total_tokens": int(total_tokens),
        "estimated_openrouter_cost_usd": estimate_openrouter_cost(total_input, total_output),
        "cost_price_source": PRICE_SOURCE,
    }


def _read_rich_primer() -> str:
    text = (REPO_ROOT / "run" / "AGENTS.md").read_text(encoding="utf-8")
    marker = "# OpenFOAM Primer"
    if marker not in text:
        raise RuntimeError(f"{marker!r} not found in run/AGENTS.md")
    return text.split(marker, 1)[1].strip()


RICH_PRIMER = _read_rich_primer()
MIN_PRIMER_R = (PLUGIN_ROOT / "OPENFOAM_PRIMER_minimal.md").read_text(encoding="utf-8").strip()
MIN_PRIMER_VANILLA = (
    PLUGIN_ROOT / "OPENFOAM_PRIMER_minimal_vanilla.md"
).read_text(encoding="utf-8").strip()
ABS_MIN_PRIMER = (PLUGIN_ROOT / "OPENFOAM_PRIMER_absolute_min.md").read_text(encoding="utf-8").strip()


def build_system_prompt(config: CellConfig) -> str:
    lines = [
        "You are an OpenFOAM expert assistant focused on authoring complete OpenFOAM case inputs from natural-language simulation requirements.",
        "",
        "Your job in this benchmark setup is to create the required OpenFOAM case files directly under the task workspace.",
        "",
        "EVALUATION MODE:",
        "- You are not expected to execute the case in this benchmark run.",
        "- Focus on producing correct OpenFOAM dictionaries and case structure.",
        "",
        "ENVIRONMENT:",
        "- Working directory: `/workspace`",
        "- Write all generated case files under `/workspace/inputs/`",
        "- Put any optional notes or helper artifacts under `/workspace/outputs/`",
        "- The OpenFOAM source tree is mounted read-only at `/data/brianliu/OpenFOAM-13`",
        "",
        "CRITICAL FILE LOCATION RULES:",
        "- All case dictionaries go under `/workspace/inputs/<folder>/<file>`",
        "- Do not write case files to `/workspace` root",
        "- Respect the folder/file names requested by the task manifest",
        "- When a task requires multiple files, author all of them in a single turn if possible",
        "",
        "OPENFOAM CASE EXPECTATIONS:",
        "- Preserve Foundation OpenFOAM dictionary syntax",
        "- Keep `FoamFile` headers consistent with the target file's class/object",
        "- Match solver family, turbulence model, transport model, and boundary conditions to the prompt",
        "- Prefer case structures and keywords that match OpenFOAM Foundation tutorials",
        "- Reuse conventions from relevant tutorials rather than inventing unsupported dictionary entries",
        "",
        "WRITING RULES:",
        "- Output valid OpenFOAM dictionaries only, not explanatory prose inside case files",
        "- Preserve exact folder names such as `0`, `constant`, and `system`",
        "- Use ASCII unless the target file already requires something else",
        "- Do not invent extra files unless they are needed to make the requested case coherent",
        "- If the prompt is underspecified, infer conservatively from the nearest OpenFOAM tutorial pattern",
    ]

    if config.r:
        lines.extend(
            [
                "",
                "RETRIEVAL WORKFLOW:",
                "- Use `search_tutorials` for similar tutorial structures, file patterns, and case organization",
                "- Use `search_cases` for detailed dictionary snippets and example field/system content",
                "- Use `search_commands` for command help, utility behavior, and execution conventions",
                "- Use these retrieval tools before guessing solver-specific syntax or case patterns",
            ]
        )

    if config.x:
        lines.extend(
            [
                "",
                "VALIDATION WORKFLOW:",
                "- Use `validate_openfoam_case` before ending the turn after you finish writing the case",
                "- Use `validate_openfoam_file` when you want to check one file while iterating",
                "- Treat validation errors as actionable structural feedback, not optional warnings",
            ]
        )

    lines.extend(
        [
            "",
            "SELF-CHECK BEFORE ENDING:",
            "- Ensure every required file exists under `/workspace/inputs`",
            "- Re-check brace balance and dictionary terminators",
            "- Confirm that references across files are consistent: solver, turbulence model, phase names, patch names, transport properties, and time controls",
            "- Confirm that generated filenames and object names line up with the requested case layout",
        ]
    )

    if config.m:
        primer = MIN_PRIMER_R if config.r else MIN_PRIMER_VANILLA
    else:
        primer = ABS_MIN_PRIMER
    return "\n".join(lines) + "\n\n" + primer + "\n"


def prepare_plugin_dir(cell_name: str, config: CellConfig) -> Path:
    root = RUNTIME_PLUGIN_ROOT / cell_name.replace("+", "_plus_")
    if root.exists():
        shutil.rmtree(root)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    if config.s:
        (root / "hooks").mkdir(parents=True, exist_ok=True)
        for name in ("hooks.json", "openfoam_case_check.py", "verify_outputs.py", "verify_openfoam_post_write.py"):
            shutil.copy2(PLUGIN_ROOT / "hooks" / name, root / "hooks" / name)
    if config.r:
        shutil.copy2(PLUGIN_ROOT / "scripts" / "openfoam_rag_mcp.py", root / "scripts" / "openfoam_rag_mcp.py")
    if config.x:
        shutil.copy2(
            PLUGIN_ROOT / "scripts" / "openfoam_validate_mcp.py",
            root / "scripts" / "openfoam_validate_mcp.py",
        )
    return root


def run_one_task(
    *,
    task_dir: Path,
    result_dir: Path,
    model: str,
    api_base: str,
    plugin_dir: Path,
    vector_db_dir: Path,
    system_prompt: str,
    config: CellConfig,
    api_key_env: str,
    dry_run: bool,
    task_timeout: float | None = None,
) -> dict[str, object]:
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "inputs").mkdir(exist_ok=True)
    (result_dir / "outputs").mkdir(exist_ok=True)
    shutil.copy2(task_dir / "task_manifest.json", result_dir / "task_manifest.json")
    shutil.copy2(task_dir / "instructions.txt", result_dir / "instructions.txt")
    shutil.copy2(task_dir / "user_requirement.txt", result_dir / "user_requirement.txt")

    prompt = (task_dir / "instructions.txt").read_text(encoding="utf-8")
    # Bind the symbolic "/workspace" path to this task's actual result_dir so
    # parallel tasks do not collide on a shared on-host path. Both the user
    # prompt (instructions) and the system prompt reference "/workspace"; both
    # need the substitution.
    workspace_abs = str(result_dir.resolve())
    prompt = prompt.replace("/workspace", workspace_abs)
    task_system_prompt = system_prompt.replace("/workspace", workspace_abs)
    cmd = [
        "claude",
        "-p",
        "--verbose",
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(
        [
            "--append-system-prompt",
            task_system_prompt,
            f"--plugin-dir={plugin_dir}",
            "--output-format",
            "stream-json",
            "--permission-mode",
            "bypassPermissions",
            "--",
            prompt,
        ]
    )

    api_key = os.environ.get(api_key_env, "")
    env = os.environ.copy()
    if api_base:
        env["ANTHROPIC_BASE_URL"] = api_base
    else:
        env.pop("ANTHROPIC_BASE_URL", None)
    env["ANTHROPIC_AUTH_TOKEN"] = api_key
    env["ANTHROPIC_API_KEY"] = ""
    if model and "/" in model:
        env["ANTHROPIC_CUSTOM_MODEL_OPTION"] = model
        env["ANTHROPIC_CUSTOM_MODEL_OPTION_NAME"] = f"{model} via gateway"
    env["CLAUDE_PROJECT_DIR"] = str(result_dir)
    env["OPENFOAM_VECTOR_DB_DIR"] = str(vector_db_dir)
    env["OPENFOAM_HOOK_INPUTS_DIR"] = str(result_dir / "inputs")
    if not config.s:
        env["OPENFOAM_HOOK_DISABLE"] = "1"

    metadata = {
        "task": task_dir.name,
        "model": model,
        "api_base": api_base,
        "plugin_dir": str(plugin_dir),
        "vector_db_dir": str(vector_db_dir),
        "cell": {
            "r": config.r,
            "s": config.s,
            "x": config.x,
            "m": config.m,
        },
        "started_at": datetime.now(timezone.utc).isoformat(),
        "command": cmd,
        "dry_run": dry_run,
    }
    write_json(result_dir / "metadata.json", metadata)
    if dry_run:
        return {"task": task_dir.name, "status": "dry_run", "command": cmd}
    if not api_key:
        raise RuntimeError(f"{api_key_env} is required unless --dry-run is set")

    started = time.time()
    timed_out = False
    stdout_text = ""
    stderr_text = ""
    returncode: int | None = None
    try:
        proc = subprocess.run(
            cmd,
            cwd=result_dir,
            env=env,
            text=True,
            capture_output=True,
            timeout=task_timeout,
        )
        stdout_text = proc.stdout
        stderr_text = proc.stderr
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout_text = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr_text = exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr_text = (stderr_text or "") + f"\n[ablation] task killed after {task_timeout}s timeout\n"
        returncode = 124  # convention: GNU timeout exit code
    (result_dir / "stdout.txt").write_text(stdout_text, encoding="utf-8")
    (result_dir / "stderr.txt").write_text(stderr_text, encoding="utf-8")
    efficiency = parse_stream_json_tool_metrics(stdout_text)
    efficiency.update(parse_stream_json_token_usage(stdout_text, model))
    efficiency["elapsed_seconds"] = round(time.time() - started, 2)
    efficiency["timed_out"] = timed_out
    if task_timeout is not None:
        efficiency["task_timeout_seconds"] = task_timeout
    write_json(result_dir / "efficiency.json", efficiency)
    status = {
        "task": task_dir.name,
        "returncode": returncode,
        "elapsed_seconds": efficiency["elapsed_seconds"],
        "timed_out": timed_out,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(result_dir / "status.json", status)
    return {
        "task": task_dir.name,
        "status": "timeout" if timed_out else ("success" if returncode == 0 else "failed"),
        "returncode": returncode,
        "timed_out": timed_out,
        **efficiency,
    }


def load_existing_result(result_dir: Path) -> dict[str, object] | None:
    status_path = result_dir / "status.json"
    efficiency_path = result_dir / "efficiency.json"
    if not status_path.exists():
        return None
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    efficiency: dict[str, object] = {}
    if efficiency_path.exists():
        try:
            efficiency = json.loads(efficiency_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            efficiency = {}
    return {
        "task": status.get("task", result_dir.name),
        "status": "success" if status.get("returncode") == 0 else "failed",
        "returncode": status.get("returncode"),
        **efficiency,
    }


def run_cell(
    *,
    cell_name: str,
    tasks_root: Path,
    results_root: Path,
    model: str,
    api_base: str,
    vector_db_dir: Path,
    include: list[str] | None,
    api_key_env: str,
    num_workers: int,
    dry_run: bool,
    task_timeout: float | None = None,
) -> dict[str, object]:
    config = CELLS[cell_name]
    plugin_dir = prepare_plugin_dir(cell_name, config)
    system_prompt = build_system_prompt(config)
    run_root = results_root / cell_name.replace("+", "_plus_")
    run_root.mkdir(parents=True, exist_ok=True)

    all_task_dirs = task_dirs(tasks_root, include)
    results_by_task: dict[str, dict[str, object]] = {}
    pending: list[Path] = []
    for task_dir in all_task_dirs:
        result_dir = run_root / task_dir.name
        existing = None if dry_run else load_existing_result(result_dir)
        if existing is not None:
            results_by_task[task_dir.name] = existing
            print(json.dumps({"cell": cell_name, "resumed": True, **existing}), flush=True)
        else:
            pending.append(task_dir)

    def _run(task_dir: Path) -> dict[str, object]:
        return run_one_task(
            task_dir=task_dir,
            result_dir=run_root / task_dir.name,
            model=model,
            api_base=api_base,
            plugin_dir=plugin_dir,
            vector_db_dir=vector_db_dir,
            system_prompt=system_prompt,
            config=config,
            api_key_env=api_key_env,
            dry_run=dry_run,
            task_timeout=task_timeout,
        )

    if num_workers <= 1:
        for task_dir in pending:
            result = _run(task_dir)
            results_by_task[task_dir.name] = result
            print(json.dumps({"cell": cell_name, **result}), flush=True)
    else:
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = {pool.submit(_run, task_dir): task_dir.name for task_dir in pending}
            for future in as_completed(futures):
                task_name = futures[future]
                result = future.result()
                results_by_task[task_name] = result
                print(json.dumps({"cell": cell_name, **result}), flush=True)

    results = [results_by_task[task_dir.name] for task_dir in all_task_dirs if task_dir.name in results_by_task]

    summary = {
        "cell": cell_name,
        "config": {"r": config.r, "s": config.s, "x": config.x, "m": config.m},
        "num_workers": num_workers,
        "results": results,
        "efficiency": aggregate_efficiency(results),
    }
    write_json(run_root / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-prefix", default=f"openfoam_ablation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--cells", nargs="+", default=CELL_ORDER)
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--vector-db-dir", type=Path, default=DEFAULT_VECTOR_DB_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--include", nargs="+")
    parser.add_argument("--num-workers", type=int, default=5)
    parser.add_argument(
        "--cell-workers",
        type=int,
        default=len(CELL_ORDER),
        help=(
            "Number of cells to run in parallel. Defaults to all known cells "
            f"({len(CELL_ORDER)}) so every R/S/X/M cell launches simultaneously."
        ),
    )
    parser.add_argument(
        "--task-timeout",
        type=float,
        default=1500.0,
        help="Per-task wall-clock timeout in seconds (default: 1500 = 25 min). Set to 0 to disable.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.num_workers < 1:
        raise RuntimeError("--num-workers must be at least 1")
    if args.cell_workers < 1:
        raise RuntimeError("--cell-workers must be at least 1")
    task_timeout: float | None = args.task_timeout if args.task_timeout and args.task_timeout > 0 else None

    unknown = [cell for cell in args.cells if cell not in CELLS]
    if unknown:
        raise RuntimeError(
            f"Unknown cell(s): {', '.join(unknown)}. Valid cells: {', '.join(CELL_ORDER)}"
        )

    batch_root = args.results_root / args.run_prefix
    batch_root.mkdir(parents=True, exist_ok=True)
    batch_summary_by_cell: dict[str, dict[str, object]] = {}

    def _run_cell(cell_name: str) -> dict[str, object]:
        return run_cell(
            cell_name=cell_name,
            tasks_root=args.tasks_root,
            results_root=batch_root,
            model=args.model,
            api_base=args.api_base,
            vector_db_dir=args.vector_db_dir,
            include=args.include,
            api_key_env=args.api_key_env,
            num_workers=args.num_workers,
            dry_run=args.dry_run,
            task_timeout=task_timeout,
        )

    if args.cell_workers <= 1:
        for cell_name in args.cells:
            batch_summary_by_cell[cell_name] = _run_cell(cell_name)
    else:
        with ThreadPoolExecutor(max_workers=args.cell_workers) as pool:
            futures = {pool.submit(_run_cell, cell_name): cell_name for cell_name in args.cells}
            for future in as_completed(futures):
                cell_name = futures[future]
                batch_summary_by_cell[cell_name] = future.result()

    batch_summary = [
        {
            "cell": cell_name,
            "run_dir": str(batch_root / cell_name.replace("+", "_plus_")),
            "efficiency": batch_summary_by_cell[cell_name].get("efficiency", {}),
        }
        for cell_name in args.cells
    ]

    write_json(batch_root / "batch_summary.json", {"runs": batch_summary})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
