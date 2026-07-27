#!/usr/bin/env python3
"""Run Foam-Agent on the same FoamGPT subset used by repo3_openfoam."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FOAM_AGENT_ROOT = Path("/home/brianliu/Foam-Agent")
DEFAULT_FOAM_AGENT_PYTHON = FOAM_AGENT_ROOT / ".venv" / "bin" / "python"
DEFAULT_TASKS_ROOT = (
    REPO_ROOT / "data" / "openfoam_benchmark" / "foamgpt_subset_seed42" / "tasks"
)
DEFAULT_RESULTS_ROOT = REPO_ROOT / "data" / "openfoam_runs" / "foam_agent"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_OPENFOAM_PATH = Path("/data/brianliu/OpenFOAM-13")
DEFAULT_EXECUTION_MODE = "execute"

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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def task_dirs(tasks_root: Path, include: list[str] | None) -> list[Path]:
    tasks_root = tasks_root.expanduser().resolve()
    tasks = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if include:
        names = set(include)
        tasks = [task for task in tasks if task.name in names]
    return tasks


def parse_foam_agent_efficiency(stdout_text: str, result_dir: Path | None = None) -> dict[str, object]:
    metrics: dict[str, object] = {
        "tool_count_definition": "llm_service_calls",
        "tool_calls": 0,
        "generated_file_events": stdout_text.count("<generating_file>"),
        "saved_file_events": stdout_text.count("Saved file at "),
        "review_loops": stdout_text.count("<reviewer>"),
        "lint_checker_invocations": stdout_text.count("<lint_checker>"),
        "retrieval_queries": stdout_text.count("Retrieved 10 candidates from FAISS."),
    }

    patterns = {
        "tool_calls": r"Total calls:\s+(\d+)",
        "failed_calls": r"Failed calls:\s+(\d+)",
        "retry_count": r"Total retries:\s+(\d+)",
        "prompt_tokens": r"Total prompt tokens:\s+(\d+)",
        "completion_tokens": r"Total completion tokens:\s+(\d+)",
        "total_tokens": r"Total tokens:\s+(\d+)",
        "api_usage_calls": r"API usage calls:\s+(\d+)",
        "estimated_usage_calls": r"Estimated usage calls:\s+(\d+)",
        "api_prompt_tokens": r"API prompt tokens:\s+(\d+)",
        "api_completion_tokens": r"API completion tokens:\s+(\d+)",
        "api_total_tokens": r"API total tokens:\s+(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, stdout_text)
        if match:
            metrics[key] = int(match.group(1))

    # Fallback: the workflow may raise before print_statistics() runs, in which
    # case stdout has no stats block. The patched LLMService writes a running
    # ledger to llm_stats.json after every call, so read that if present and the
    # stdout did not already provide richer numbers.
    if result_dir is not None:
        stats_path = result_dir / "llm_stats.json"
        if stats_path.exists():
            try:
                ledger = json.loads(stats_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                ledger = {}
            ledger_map = {
                "tool_calls": "total_calls",
                "failed_calls": "failed_calls",
                "retry_count": "retry_count",
                "prompt_tokens": "total_prompt_tokens",
                "completion_tokens": "total_completion_tokens",
                "total_tokens": "total_tokens",
                "api_usage_calls": "api_usage_calls",
                "estimated_usage_calls": "estimated_usage_calls",
                "api_prompt_tokens": "api_prompt_tokens",
                "api_completion_tokens": "api_completion_tokens",
                "api_total_tokens": "api_total_tokens",
            }
            for metric_key, ledger_key in ledger_map.items():
                if ledger_key in ledger and metrics.get(metric_key, 0) in (0, None):
                    metrics[metric_key] = ledger[ledger_key]
            metrics["stats_source"] = "stdout+ledger"
        else:
            metrics["stats_source"] = "stdout"

    # Token reliability: API-sourced usage is trustworthy; estimated fallback is
    # tiktoken-based. Report whether all calls were API-sourced.
    api_calls = int(metrics.get("api_usage_calls", 0) or 0)
    est_calls = int(metrics.get("estimated_usage_calls", 0) or 0)
    metrics["tokens_all_api_sourced"] = (api_calls > 0 and est_calls == 0)
    metrics["estimated_openrouter_cost_usd"] = estimate_openrouter_cost(
        float(metrics.get("prompt_tokens", 0) or 0),
        float(metrics.get("completion_tokens", 0) or 0),
    )
    metrics["cost_price_source"] = PRICE_SOURCE
    return metrics


def aggregate_efficiency(results: list[dict[str, object]]) -> dict[str, object]:
    completed = [result for result in results if "elapsed_seconds" in result]
    if not completed:
        return {}

    def mean_for(key: str) -> float:
        values = [float(result.get(key, 0)) for result in completed]
        return round(sum(values) / len(values), 4)

    total_prompt = sum(float(result.get("prompt_tokens", 0) or 0) for result in completed)
    total_completion = sum(float(result.get("completion_tokens", 0) or 0) for result in completed)
    total_tokens = sum(float(result.get("total_tokens", 0) or 0) for result in completed)
    all_api_sourced = all(bool(result.get("tokens_all_api_sourced")) for result in completed)

    summary = {
        "tool_count_definition": "llm_service_calls",
        "n_tasks": len(completed),
        "mean_wall_seconds": mean_for("elapsed_seconds"),
        "mean_tools_per_task": mean_for("tool_calls"),
        "mean_prompt_tokens_per_task": mean_for("prompt_tokens"),
        "mean_completion_tokens_per_task": mean_for("completion_tokens"),
        "mean_total_tokens_per_task": mean_for("total_tokens"),
        "mean_api_usage_calls_per_task": mean_for("api_usage_calls"),
        "mean_estimated_usage_calls_per_task": mean_for("estimated_usage_calls"),
        "total_prompt_tokens": int(total_prompt),
        "total_completion_tokens": int(total_completion),
        "total_tokens": int(total_tokens),
        "tokens_all_api_sourced": all_api_sourced,
        "estimated_openrouter_cost_usd": estimate_openrouter_cost(total_prompt, total_completion),
        "cost_price_source": PRICE_SOURCE,
        "mean_generated_file_events_per_task": mean_for("generated_file_events"),
        "mean_saved_file_events_per_task": mean_for("saved_file_events"),
        "mean_review_loops_per_task": mean_for("review_loops"),
        "mean_lint_checker_invocations_per_task": mean_for("lint_checker_invocations"),
        "mean_retrieval_queries_per_task": mean_for("retrieval_queries"),
    }
    return summary


def resolve_openfoam_path(cli_value: Path | None) -> Path:
    candidates: list[Path] = []
    if cli_value is not None:
        candidates.append(cli_value)
    env_value = os.environ.get("WM_PROJECT_DIR")
    if env_value:
        candidates.append(Path(env_value))
    candidates.append(DEFAULT_OPENFOAM_PATH)

    for candidate in candidates:
        if (candidate / "etc" / "bashrc").exists():
            return candidate
    checked = ", ".join(str(path) for path in candidates)
    raise RuntimeError(
        "Could not resolve an OpenFOAM installation with etc/bashrc. "
        f"Checked: {checked}"
    )


def build_env(
    openrouter_key: str,
    model: str,
    openai_base_url: str,
    embedding_model: str,
    openfoam_path: Path,
    python_executable: Path,
    stats_path: Path | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    if stats_path is not None:
        env["FOAMAGENT_STATS_PATH"] = str(stats_path)
    env["FOAMAGENT_MODEL_PROVIDER"] = "openai"
    env["FOAMAGENT_MODEL_VERSION"] = model
    env["FOAMAGENT_EMBEDDING_PROVIDER"] = "openai"
    env["FOAMAGENT_EMBEDDING_MODEL"] = embedding_model
    env["OPENAI_API_KEY"] = openrouter_key
    env["OPENAI_BASE_URL"] = openai_base_url
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["WM_PROJECT_DIR"] = str(openfoam_path)
    hf_home = str(FOAM_AGENT_ROOT / ".hf-cache")
    env["HF_HOME"] = hf_home
    env["HUGGINGFACE_HUB_CACHE"] = str(Path(hf_home) / "hub")
    env["TRANSFORMERS_CACHE"] = str(Path(hf_home) / "transformers")
    env["VIRTUAL_ENV"] = str(python_executable.parent.parent)
    env["PATH"] = f"{python_executable.parent}:{env.get('PATH', '')}"
    Path(env["HF_HOME"]).mkdir(parents=True, exist_ok=True)
    Path(env["HUGGINGFACE_HUB_CACHE"]).mkdir(parents=True, exist_ok=True)
    Path(env["TRANSFORMERS_CACHE"]).mkdir(parents=True, exist_ok=True)
    return env


def run_task(
    task_dir: Path,
    run_root: Path,
    model: str,
    openai_base_url: str,
    embedding_model: str,
    openfoam_path: Path | None,
    openrouter_key: str,
    dry_run: bool,
    execution_mode: str,
    python_executable: Path,
) -> dict[str, object]:
    result_dir = run_root / task_dir.name
    result_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = (task_dir / "user_requirement.txt").resolve()
    cmd = [
        str(python_executable),
        str(FOAM_AGENT_ROOT / "foambench_main.py"),
        "--output",
        str(result_dir / "inputs"),
        "--prompt_path",
        str(prompt_path),
        "--execution_mode",
        execution_mode,
    ]
    if openfoam_path is not None:
        cmd[2:2] = ["--openfoam_path", str(openfoam_path)]
    metadata = {
        "task": task_dir.name,
        "model": model,
        "openai_base_url": openai_base_url,
        "embedding_provider": "openai",
        "embedding_model": embedding_model,
        "openfoam_path": str(openfoam_path) if openfoam_path is not None else None,
        "prompt_path": str(prompt_path),
        "command": cmd,
        "dry_run": dry_run,
        "execution_mode": execution_mode,
    }
    write_json(result_dir / "metadata.json", metadata)
    if dry_run:
        result = {"task": task_dir.name, "status": "dry_run", "command": cmd}
        print(json.dumps(result), flush=True)
        return result

    started = time.time()
    env = build_env(
        openrouter_key=openrouter_key,
        model=model,
        openai_base_url=openai_base_url,
        embedding_model=embedding_model,
        openfoam_path=openfoam_path or DEFAULT_OPENFOAM_PATH,
        python_executable=python_executable,
        stats_path=result_dir / "llm_stats.json",
    )
    proc = subprocess.run(
        cmd,
        cwd=FOAM_AGENT_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    (result_dir / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (result_dir / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    efficiency = parse_foam_agent_efficiency(proc.stdout, result_dir)
    efficiency["elapsed_seconds"] = round(time.time() - started, 2)
    write_json(result_dir / "efficiency.json", efficiency)
    status = {
        "task": task_dir.name,
        "returncode": proc.returncode,
        "elapsed_seconds": efficiency["elapsed_seconds"],
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(result_dir / "status.json", status)
    result = {
        "task": task_dir.name,
        "status": "success" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        **efficiency,
    }
    print(json.dumps(result), flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--openai-base-url", default=DEFAULT_OPENAI_BASE_URL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--openfoam-path", type=Path)
    parser.add_argument("--execution-mode", choices=["execute", "lint_only"], default=DEFAULT_EXECUTION_MODE)
    parser.add_argument("--python-executable", type=Path, default=DEFAULT_FOAM_AGENT_PYTHON)
    parser.add_argument("--include", nargs="+")
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.num_workers < 1:
        raise RuntimeError("--num-workers must be at least 1")

    run_root = args.results_root / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    python_executable = args.python_executable.expanduser()
    if not python_executable.exists():
        raise RuntimeError(f"Foam-Agent python executable not found: {python_executable}")
    openfoam_path = None
    if args.execution_mode == "execute":
        openfoam_path = resolve_openfoam_path(args.openfoam_path)
    tasks = task_dirs(args.tasks_root, args.include)

    results = []
    if not args.dry_run and not openrouter_key:
        raise RuntimeError("OPENROUTER_API_KEY is required unless --dry-run is set")

    if args.num_workers == 1:
        for task_dir in tasks:
            results.append(
                run_task(
                    task_dir=task_dir,
                    run_root=run_root,
                    model=args.model,
                    openai_base_url=args.openai_base_url,
                    embedding_model=args.embedding_model,
                    openfoam_path=openfoam_path,
                    openrouter_key=openrouter_key,
                    dry_run=args.dry_run,
                    execution_mode=args.execution_mode,
                    python_executable=python_executable,
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=args.num_workers) as pool:
            futures = {
                pool.submit(
                    run_task,
                    task_dir,
                    run_root,
                    args.model,
                    args.openai_base_url,
                    args.embedding_model,
                    openfoam_path,
                    openrouter_key,
                    args.dry_run,
                    args.execution_mode,
                    python_executable,
                ): task_dir.name
                for task_dir in tasks
            }
            for future in as_completed(futures):
                results.append(future.result())

    results.sort(key=lambda item: str(item["task"]))
    write_json(
        run_root / "run_summary.json",
        {
            "results": results,
            "num_workers": args.num_workers,
            "openfoam_path": str(openfoam_path) if openfoam_path is not None else None,
            "execution_mode": args.execution_mode,
            "efficiency": aggregate_efficiency(results),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
