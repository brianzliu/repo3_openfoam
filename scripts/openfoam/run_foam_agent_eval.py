#!/usr/bin/env python3
"""Run Foam-Agent on the same FoamGPT subset used by repo3_openfoam."""

from __future__ import annotations

import argparse
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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def task_dirs(tasks_root: Path, include: list[str] | None) -> list[Path]:
    tasks = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if include:
        names = set(include)
        tasks = [task for task in tasks if task.name in names]
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--openai-base-url", default=DEFAULT_OPENAI_BASE_URL)
    parser.add_argument("--include", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_root = args.results_root / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

    results = []
    for task_dir in task_dirs(args.tasks_root, args.include):
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
        ]
        metadata = {
            "task": task_dir.name,
            "model": args.model,
            "openai_base_url": args.openai_base_url,
            "prompt_path": str(prompt_path),
            "command": cmd,
            "dry_run": args.dry_run,
        }
        write_json(result_dir / "metadata.json", metadata)
        if args.dry_run:
            result = {"task": task_dir.name, "status": "dry_run", "command": cmd}
            results.append(result)
            print(json.dumps(result))
            continue
        if not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY is required unless --dry-run is set")

        env = os.environ.copy()
        env["FOAMAGENT_MODEL_PROVIDER"] = "openai"
        env["FOAMAGENT_MODEL_VERSION"] = args.model
        env["OPENAI_API_KEY"] = openrouter_key
        env["OPENAI_BASE_URL"] = args.openai_base_url

        started = time.time()
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
        results.append(result)
        print(json.dumps(result))

    write_json(run_root / "run_summary.json", {"results": results})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
