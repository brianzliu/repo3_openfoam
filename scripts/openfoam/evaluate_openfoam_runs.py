#!/usr/bin/env python3
"""Evaluate OpenFOAM benchmark runs against the materialized FoamGPT ground truth."""

from __future__ import annotations

import argparse
import json
import statistics
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK_ROOT = REPO_ROOT / "data" / "openfoam_benchmark" / "foamgpt_subset_seed42"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        lines.append(" ".join(line.split()))
    return "\n".join(lines)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=normalize_text(a), b=normalize_text(b)).ratio()


def evaluate_agent_run(run_dir: Path, manifest: dict[str, Any], gt_root: Path) -> dict[str, Any]:
    per_case = []
    overall_scores = []
    for case in manifest["cases"]:
        case_name = case["case_name"]
        required_files = case["required_files"]
        generated_root = run_dir / case_name / "inputs"
        gt_case_root = gt_root / case_name / "inputs"

        file_scores = []
        missing = []
        exact = 0
        for rel in required_files:
            gt_path = gt_case_root / rel
            gen_path = generated_root / rel
            if not gen_path.exists():
                missing.append(rel)
                file_scores.append(0.0)
                continue
            gt_text = gt_path.read_text(encoding="utf-8", errors="ignore")
            gen_text = gen_path.read_text(encoding="utf-8", errors="ignore")
            score = similarity(gt_text, gen_text)
            file_scores.append(score)
            if normalize_text(gt_text) == normalize_text(gen_text):
                exact += 1

        mean_similarity = statistics.mean(file_scores) if file_scores else 0.0
        coverage = 1.0 - (len(missing) / len(required_files)) if required_files else 1.0
        overall = 0.7 * mean_similarity + 0.3 * coverage
        overall_scores.append(overall)
        per_case.append(
            {
                "case_name": case_name,
                "required_file_count": len(required_files),
                "missing_files": missing,
                "coverage": coverage,
                "exact_match_rate": (exact / len(required_files)) if required_files else 1.0,
                "mean_similarity": mean_similarity,
                "overall_score": overall,
            }
        )

    return {
        "run_dir": str(run_dir),
        "n_cases": len(per_case),
        "mean_overall_score": statistics.mean(overall_scores) if overall_scores else 0.0,
        "per_case": per_case,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument(
        "--agent-run",
        action="append",
        default=[],
        help="Label=path pair, e.g. repo3=/path/to/run or foam_agent=/path/to/run",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    manifest = load_json(args.benchmark_root / "manifest.json")
    gt_root = args.benchmark_root / "gt"

    results = {}
    for spec in args.agent_run:
        label, path = spec.split("=", 1)
        results[label] = evaluate_agent_run(Path(path), manifest, gt_root)

    payload = {
        "benchmark_root": str(args.benchmark_root),
        "results": results,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
