#!/usr/bin/env python3
"""Run Foam-Agent on the same FoamGPT subset used by repo3_openfoam."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FOAM_AGENT_ROOT = Path("/home/brianliu/Foam-Agent")
DEFAULT_TASKS_ROOT = (
    REPO_ROOT / "data" / "openfoam_benchmark" / "foamgpt_subset_seed42" / "tasks"
)
DEFAULT_RESULTS_ROOT = REPO_ROOT / "data" / "openfoam_runs" / "foam_agent"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_OPENFOAM_PATH = Path("/data/brianliu/OpenFOAM-13")
DEFAULT_EXECUTION_MODE = "execute"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def task_dirs(tasks_root: Path, include: list[str] | None) -> list[Path]:
    tasks = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if include:
        names = set(include)
        tasks = [task for task in tasks if task.name in names]
    return tasks


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
) -> dict[str, str]:
    env = os.environ.copy()
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
) -> dict[str, object]:
    result_dir = run_root / task_dir.name
    result_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = task_dir / "user_requirement.txt"
    cmd = [
        sys.executable,
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
    status = {
        "task": task_dir.name,
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.time() - started, 2),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(result_dir / "status.json", status)
    result = {
        "task": task_dir.name,
        "status": "success" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
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
    parser.add_argument("--include", nargs="+")
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.num_workers < 1:
        raise RuntimeError("--num-workers must be at least 1")

    run_root = args.results_root / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
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
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
