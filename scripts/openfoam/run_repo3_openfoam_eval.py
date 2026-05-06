#!/usr/bin/env python3
"""Run the repo3_openfoam Claude Code plugin on a FoamGPT subset."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASKS_ROOT = (
    REPO_ROOT / "data" / "openfoam_benchmark" / "foamgpt_subset_seed42" / "tasks"
)
DEFAULT_RESULTS_ROOT = REPO_ROOT / "data" / "openfoam_runs" / "repo3_openfoam"
DEFAULT_PLUGIN_DIR = REPO_ROOT / "plugin"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_API_BASE = "https://openrouter.ai/api/anthropic"


def load_prompt(task_dir: Path) -> str:
    return (task_dir / "instructions.txt").read_text(encoding="utf-8")


def load_system_prompt() -> str:
    return (REPO_ROOT / "run" / "AGENTS.md").read_text(encoding="utf-8")


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


def aggregate_efficiency(results: list[dict[str, object]]) -> dict[str, object]:
    completed = [result for result in results if "elapsed_seconds" in result]
    if not completed:
        return {}

    def mean_for(key: str) -> float:
        values = [float(result.get(key, 0)) for result in completed]
        return round(sum(values) / len(values), 4)

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
    }


def run_one_task(
    *,
    task_dir: Path,
    result_dir: Path,
    model: str,
    api_base: str,
    plugin_dir: Path,
    vector_db_dir: Path,
    dry_run: bool,
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "inputs").mkdir(exist_ok=True)
    (result_dir / "outputs").mkdir(exist_ok=True)
    shutil.copy2(task_dir / "task_manifest.json", result_dir / "task_manifest.json")
    shutil.copy2(task_dir / "instructions.txt", result_dir / "instructions.txt")
    shutil.copy2(task_dir / "user_requirement.txt", result_dir / "user_requirement.txt")

    prompt = load_prompt(task_dir)
    system_prompt = load_system_prompt()
    cmd = [
        "claude",
        "-p",
        "--model",
        model,
        "--append-system-prompt",
        system_prompt,
        f"--plugin-dir={plugin_dir}",
        "--output-format",
        "stream-json",
        "--permission-mode",
        "bypassPermissions",
        "--",
        prompt,
    ]

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = api_base
    env["ANTHROPIC_API_KEY"] = openrouter_key
    env["ANTHROPIC_AUTH_TOKEN"] = openrouter_key
    env["CLAUDE_PROJECT_DIR"] = str(result_dir)
    env["OPENFOAM_VECTOR_DB_DIR"] = str(vector_db_dir)
    env["OPENFOAM_HOOK_INPUTS_DIR"] = str(result_dir / "inputs")

    metadata = {
        "task": task_dir.name,
        "model": model,
        "api_base": api_base,
        "plugin_dir": str(plugin_dir),
        "vector_db_dir": str(vector_db_dir),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "command": cmd,
        "dry_run": dry_run,
    }
    write_json(result_dir / "metadata.json", metadata)
    if dry_run:
        return {"task": task_dir.name, "status": "dry_run", "command": cmd}
    if not openrouter_key:
        raise RuntimeError("OPENROUTER_API_KEY is required unless --dry-run is set")

    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=result_dir,
        env=env,
        text=True,
        capture_output=True,
    )
    (result_dir / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (result_dir / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    efficiency = parse_stream_json_tool_metrics(proc.stdout)
    efficiency["elapsed_seconds"] = round(time.time() - started, 2)
    write_json(result_dir / "efficiency.json", efficiency)
    status = {
        "task": task_dir.name,
        "returncode": proc.returncode,
        "elapsed_seconds": efficiency["elapsed_seconds"],
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(result_dir / "status.json", status)
    return {
        "task": task_dir.name,
        "status": "success" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        **efficiency,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--plugin-dir", type=Path, default=DEFAULT_PLUGIN_DIR)
    parser.add_argument(
        "--vector-db-dir",
        type=Path,
        default=REPO_ROOT / "data" / "openfoam_benchmark" / "chromadb_openfoam",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--include", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_root = args.results_root / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)

    results = []
    for task_dir in task_dirs(args.tasks_root, args.include):
        result = run_one_task(
            task_dir=task_dir,
            result_dir=run_root / task_dir.name,
            model=args.model,
            api_base=args.api_base,
            plugin_dir=args.plugin_dir,
            vector_db_dir=args.vector_db_dir,
            dry_run=args.dry_run,
        )
        results.append(result)
        print(json.dumps(result))

    write_json(
        run_root / "run_summary.json",
        {
            "results": results,
            "efficiency": aggregate_efficiency(results),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
