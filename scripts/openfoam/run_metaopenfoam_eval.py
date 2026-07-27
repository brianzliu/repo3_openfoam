#!/usr/bin/env python3
"""Run MetaOpenFOAM on the materialized FoamGPT OpenFOAM benchmark subset."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
META_ROOT = Path("/home/brianliu/MetaOpenFOAM")
DEFAULT_META_PYTHON = META_ROOT / ".venv" / "bin" / "python"
DEFAULT_RESULTS_ROOT = REPO_ROOT / "data" / "openfoam_runs" / "metaopenfoam"
DEFAULT_TASKS_ROOT = REPO_ROOT / "data" / "openfoam_benchmark" / "foamgpt_subset_seed42_n30_hybrid" / "tasks"
DEFAULT_OPENFOAM_PATH = Path("/data/brianliu/OpenFOAM-13")
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_OPENAI_BASE_URL = "https://openrouter.ai/api/v1"

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
        include_set = set(include)
        tasks = [task for task in tasks if task.name in include_set]
    return tasks


def parse_metaopenfoam_efficiency(stdout_text: str, run_dir: Path) -> dict[str, object]:
    # Robust LLM-call count: MetaOpenFOAM's deepseek path prints exactly one
    # "DeepSeek response keys:" line per model invocation (see
    # MetaOpenFOAM/src/qa_module.py get_deepseek_response). That is a far more
    # faithful per-call counter than the previous token/stat-event proxy, which
    # only fired once per run from the final statistics block.
    llm_calls = stdout_text.count("DeepSeek response keys:")
    metrics: dict[str, object] = {
        "tool_count_definition": "metaopenfoam_llm_calls",
        "tool_calls": llm_calls,
        "llm_calls": llm_calls,
        "generated_file_events": len(re.findall(r"saved? file|Save file|write", stdout_text, flags=re.I)),
        "review_loops": stdout_text.count("review_subtasks") + stdout_text.count("<reviewer>"),
        "lint_checker_invocations": stdout_text.count("[metaopenfoam-lint]"),
        "retrieval_queries": stdout_text.count("source_documents") + stdout_text.count("find_case"),
    }

    stats_paths = [run_dir / "statistics.txt", run_dir / "ave_statistics.txt"]
    for stats_path in stats_paths:
        if not stats_path.exists():
            continue
        text = stats_path.read_text(encoding="utf-8", errors="ignore")
        patterns = {
            "prompt_tokens": r"Prompt Tokens:\s*([0-9.]+)",
            "completion_tokens": r"Completion Tokens:\s*([0-9.]+)",
            "total_tokens": r"Total Tokens:\s*([0-9.]+)",
            "running_time": r"Running Time:\s*([0-9.]+)",
            "number_of_input_files": r"Number of Input Files:\s*([0-9.]+)",
            "total_lines_of_inputs": r"Total Lines of Inputs:\s*([0-9.]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if not match:
                continue
            value = float(match.group(1))
            metrics[key] = int(value) if value.is_integer() else value

    if "prompt_tokens" in metrics or "completion_tokens" in metrics:
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

    def mean_for(key: str) -> float | None:
        vals = [float(result[key]) for result in completed if key in result]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 4)

    summary: dict[str, object] = {
        "tool_count_definition": "metaopenfoam_llm_calls",
        "n_tasks": len(completed),
        "mean_wall_seconds": mean_for("elapsed_seconds"),
        "mean_tools_per_task": mean_for("tool_calls"),
        "mean_llm_calls_per_task": mean_for("llm_calls"),
    }
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "generated_file_events",
        "review_loops",
        "lint_checker_invocations",
        "retrieval_queries",
        "number_of_input_files",
        "total_lines_of_inputs",
    ):
        value = mean_for(key)
        if value is not None:
            summary[f"mean_{key}_per_task"] = value

    total_prompt = sum(float(result.get("prompt_tokens", 0) or 0) for result in completed)
    total_completion = sum(float(result.get("completion_tokens", 0) or 0) for result in completed)
    total_tokens = sum(float(result.get("total_tokens", 0) or 0) for result in completed)
    summary["total_prompt_tokens"] = int(total_prompt)
    summary["total_completion_tokens"] = int(total_completion)
    summary["total_tokens"] = int(total_tokens)
    summary["estimated_openrouter_cost_usd"] = estimate_openrouter_cost(total_prompt, total_completion)
    summary["cost_price_source"] = PRICE_SOURCE
    return summary


def write_meta_config(config_path: Path, task_dir: Path, result_dir: Path, args: argparse.Namespace) -> None:
    prompt = (task_dir / "user_requirement.txt").read_text(encoding="utf-8")
    payload = {
        "usr_requirment": prompt,
        "max_loop": args.max_loop,
        "temperature": args.temperature,
        "batchsize": args.batchsize,
        "searchdocs": args.searchdocs,
        "run_times": 1,
        "MetaGPT_PATH": str(META_ROOT),
        "DEEPSEEK_API_KEY": os.environ.get(args.api_key_env, ""),
        "DEEPSEEK_BASE_URL": args.openai_base_url,
        "model": args.model,
        "benchmark_case_path": str(result_dir / "inputs"),
        "lint_only": True,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def write_metagpt_config(api_key: str, model: str, base_url: str) -> None:
    config_dir = META_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "llm": {
            "api_type": "openai",
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "stream": False,
            "temperature": 0.0,
        }
    }
    (config_dir / "config2.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def build_env(args: argparse.Namespace, config_path: Path, python_executable: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CONFIG_FILE_PATH"] = str(config_path)
    env["WM_PROJECT_DIR"] = str(args.openfoam_path)
    env["PYTHONPATH"] = f"{META_ROOT / 'src'}:{META_ROOT}:{env.get('PYTHONPATH', '')}"
    env["VIRTUAL_ENV"] = str(python_executable.parent.parent)
    env["PATH"] = f"{python_executable.parent}:{env.get('PATH', '')}"
    env["OPENAI_API_KEY"] = os.environ.get(args.api_key_env, "")
    env["OPENAI_BASE_URL"] = args.openai_base_url
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["METAOPENFOAM_LINT_ONLY"] = "1"
    env["HF_HOME"] = "/home/brianliu/.cache/huggingface-metaopenfoam"
    env["SENTENCE_TRANSFORMERS_HOME"] = "/home/brianliu/.cache/sentence-transformers-metaopenfoam"
    env["METAOPENFOAM_EMBEDDING_MODEL"] = "sentence-transformers/all-MiniLM-L6-v2"
    return env


def run_task(
    task_dir: Path,
    run_root: Path,
    args: argparse.Namespace,
    python_executable: Path,
    dry_run: bool,
) -> dict[str, object]:
    result_dir = run_root / task_dir.name
    inputs_dir = result_dir / "inputs"
    result_dir.mkdir(parents=True, exist_ok=True)
    config_path = result_dir / "metaopenfoam_config.yaml"
    write_meta_config(config_path, task_dir, result_dir, args)

    cmd = [
        str(python_executable),
        str(META_ROOT / "src" / "OptMetaOpenfoam.py"),
    ]
    metadata = {
        "task": task_dir.name,
        "model": args.model,
        "openai_base_url": args.openai_base_url,
        "prompt_path": str((task_dir / "user_requirement.txt").resolve()),
        "config_path": str(config_path),
        "command": cmd,
        "dry_run": dry_run,
        "execution_mode": "lint_only",
    }
    write_json(result_dir / "metadata.json", metadata)
    if dry_run:
        result = {"task": task_dir.name, "status": "dry_run", "command": cmd}
        print(json.dumps(result), flush=True)
        return result

    if inputs_dir.exists():
        shutil.rmtree(inputs_dir)
    started = time.time()
    env = build_env(args, config_path, python_executable)
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            cwd=META_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=args.task_timeout,
        )
        stdout_text = proc.stdout
        stderr_text = proc.stderr
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout_text = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr_text = exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr_text += f"\n[metaopenfoam] task killed after {args.task_timeout}s timeout\n"
        returncode = 124

    (result_dir / "stdout.txt").write_text(stdout_text, encoding="utf-8")
    (result_dir / "stderr.txt").write_text(stderr_text, encoding="utf-8")

    # MetaOpenFOAM writes into its global run directory. Preserve the requested
    # benchmark output location if the config-directed path was ignored.
    if not inputs_dir.exists():
        inferred = latest_case_dir_from_stdout(stdout_text)
        if inferred and inferred.exists():
            shutil.copytree(inferred, inputs_dir, dirs_exist_ok=True)

    efficiency = parse_metaopenfoam_efficiency(stdout_text, inputs_dir)
    efficiency["elapsed_seconds"] = round(time.time() - started, 2)
    efficiency["timed_out"] = timed_out
    write_json(result_dir / "efficiency.json", efficiency)
    status = {
        "task": task_dir.name,
        "returncode": returncode,
        "elapsed_seconds": efficiency["elapsed_seconds"],
        "timed_out": timed_out,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(result_dir / "status.json", status)
    result = {
        "task": task_dir.name,
        "status": "timeout" if timed_out else ("success" if returncode == 0 else "failed"),
        "returncode": returncode,
        **efficiency,
    }
    print(json.dumps(result), flush=True)
    return result


def latest_case_dir_from_stdout(stdout_text: str) -> Path | None:
    paths = re.findall(r"/home/brianliu/MetaOpenFOAM/run/[^\s'\"]+", stdout_text)
    candidates = [Path(path.rstrip(",)")) for path in paths]
    existing = [path for path in candidates if path.exists() and path.is_dir()]
    if existing:
        return max(existing, key=lambda path: path.stat().st_mtime)
    run_root = META_ROOT / "run"
    dirs = [path for path in run_root.iterdir() if path.is_dir()]
    return max(dirs, key=lambda path: path.stat().st_mtime) if dirs else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--python-executable", type=Path, default=DEFAULT_META_PYTHON)
    parser.add_argument("--openfoam-path", type=Path, default=DEFAULT_OPENFOAM_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--openai-base-url", default=DEFAULT_OPENAI_BASE_URL)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--include", nargs="+")
    parser.add_argument("--num-workers", type=int, default=15)
    parser.add_argument("--task-timeout", type=float, default=1500.0)
    parser.add_argument("--max-loop", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--batchsize", type=int, default=10)
    parser.add_argument("--searchdocs", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.num_workers < 1:
        raise RuntimeError("--num-workers must be at least 1")
    python_executable = args.python_executable.expanduser()
    if not python_executable.exists():
        raise RuntimeError(f"MetaOpenFOAM python executable not found: {python_executable}")
    if not args.dry_run and not os.environ.get(args.api_key_env):
        raise RuntimeError(f"{args.api_key_env} is required unless --dry-run is set")

    run_root = args.results_root / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    write_metagpt_config(os.environ.get(args.api_key_env, ""), args.model, args.openai_base_url)

    tasks = task_dirs(args.tasks_root, args.include)
    results: list[dict[str, object]] = []
    if args.num_workers == 1:
        for task_dir in tasks:
            results.append(run_task(task_dir, run_root, args, python_executable, args.dry_run))
    else:
        with ThreadPoolExecutor(max_workers=args.num_workers) as pool:
            futures = {
                pool.submit(run_task, task_dir, run_root, args, python_executable, args.dry_run): task_dir.name
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
            "execution_mode": "lint_only",
            "model": args.model,
            "efficiency": aggregate_efficiency(results),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
