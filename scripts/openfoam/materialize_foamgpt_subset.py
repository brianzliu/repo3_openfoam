#!/usr/bin/env python3
"""Materialize a small OpenFOAM benchmark subset from FoamGPT.

Creates:
- a task manifest with per-case metadata
- prompt/instructions files for each task
- ground-truth case trees under ``gt/<case>/inputs``

This is intentionally analogous to repo_3's task materialization flow, but the
source of truth is FoamGPT's file-level JSONL data instead of GEOS XML tasks.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def choose_cases(rows: list[dict[str, Any]], sample_size: int, seed: int) -> list[str]:
    case_names = sorted({row["case_name"] for row in rows})
    rng = random.Random(seed)
    return rng.sample(case_names, sample_size)


def build_case_payload(case_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    case_rows = [row for row in rows if row["case_name"] == case_name]
    if not case_rows:
        raise ValueError(f"Case not found: {case_name}")

    exemplar = case_rows[0]
    files = []
    for row in sorted(case_rows, key=lambda item: (item["folder_name"], item["file_name"])):
        files.append(
            {
                "folder_name": row["folder_name"],
                "file_name": row["file_name"],
                "relative_path": f"{row['folder_name']}/{row['file_name']}",
                "file_content": row["file_content"],
            }
        )

    return {
        "case_name": case_name,
        "case_solver": exemplar["case_solver"],
        "case_domain": exemplar["case_domain"],
        "case_category": exemplar["case_category"],
        "user_requirement": exemplar["user_requirement"],
        "required_files": [item["relative_path"] for item in files],
        "files": files,
    }


def write_task(task_dir: Path, payload: dict[str, Any]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    gt_inputs = task_dir.parent.parent / "gt" / payload["case_name"] / "inputs"
    gt_inputs.mkdir(parents=True, exist_ok=True)

    instructions = (
        "Create a complete OpenFOAM case for the following specification.\n\n"
        f"Case name: {payload['case_name']}\n"
        f"Solver: {payload['case_solver']}\n"
        f"Domain: {payload['case_domain']}\n"
        f"Category: {payload['case_category']}\n\n"
        "Write the required files under `/workspace/inputs` using these exact paths:\n"
        + "\n".join(f"- {path}" for path in payload["required_files"])
        + "\n\nSimulation requirement:\n"
        + payload["user_requirement"].strip()
    )
    (task_dir / "instructions.txt").write_text(instructions + "\n", encoding="utf-8")
    (task_dir / "user_requirement.txt").write_text(
        payload["user_requirement"].strip() + "\n", encoding="utf-8"
    )
    (task_dir / "task_manifest.json").write_text(
        json.dumps(
            {
                "case_name": payload["case_name"],
                "case_solver": payload["case_solver"],
                "case_domain": payload["case_domain"],
                "case_category": payload["case_category"],
                "user_requirement": payload["user_requirement"],
                "required_files": payload["required_files"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    for item in payload["files"]:
        dest = gt_inputs / item["relative_path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(item["file_content"], encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "configs"
        / "openfoam_benchmark"
        / "foamgpt_subset_seed42.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "data"
        / "openfoam_benchmark"
        / "foamgpt_subset_seed42",
    )
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = load_jsonl(Path(config["dataset_path"]))

    if config.get("cases"):
        cases = list(config["cases"])
    else:
        selection = config["selection"]
        cases = choose_cases(
            rows=rows,
            sample_size=int(selection["sample_size"]),
            seed=int(selection["seed"]),
        )

    args.output_root.mkdir(parents=True, exist_ok=True)
    tasks_dir = args.output_root / "tasks"
    gt_dir = args.output_root / "gt"
    tasks_dir.mkdir(exist_ok=True)
    gt_dir.mkdir(exist_ok=True)

    manifest_cases = []
    for case_name in cases:
        payload = build_case_payload(case_name, rows)
        write_task(tasks_dir / case_name, payload)
        manifest_cases.append(
            {
                "case_name": payload["case_name"],
                "case_solver": payload["case_solver"],
                "case_domain": payload["case_domain"],
                "case_category": payload["case_category"],
                "required_files": payload["required_files"],
            }
        )

    manifest = {
        "subset_name": config["subset_name"],
        "dataset_path": config["dataset_path"],
        "output_root": str(args.output_root),
        "cases": manifest_cases,
        "selection": config["selection"],
        "model": config["model"],
    }
    (args.output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
