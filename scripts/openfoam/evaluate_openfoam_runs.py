#!/usr/bin/env python3
"""Evaluate OpenFOAM benchmark runs against the materialized FoamGPT ground truth."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK_ROOT = REPO_ROOT / "data" / "openfoam_benchmark" / "foamgpt_subset_seed42"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def parse_foam_agent_efficiency_from_stdout(stdout_text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {
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
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, stdout_text)
        if match:
            metrics[key] = int(match.group(1))
    return metrics


def parse_repo3_efficiency_from_stdout(stdout_text: str) -> dict[str, Any]:
    tool_counts: dict[str, int] = {}
    assistant_messages = 0
    parse_errors = 0

    def walk(value: object) -> None:
        nonlocal assistant_messages
        if isinstance(value, dict):
            if value.get("type") == "assistant":
                assistant_messages += 1
            if value.get("type") == "tool_use":
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
    metrics: dict[str, Any] = {
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


def infer_efficiency_from_artifacts(case_dir: Path) -> dict[str, Any] | None:
    metadata = load_optional_json(case_dir / "metadata.json") or {}
    stdout_path = case_dir / "stdout.txt"
    if not stdout_path.exists():
        return None
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="ignore")
    command = metadata.get("command") or []
    command_text = " ".join(command) if isinstance(command, list) else str(command)
    if "foambench_main.py" in command_text:
        return parse_foam_agent_efficiency_from_stdout(stdout_text)
    if "claude" in command_text:
        return parse_repo3_efficiency_from_stdout(stdout_text)
    return None


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


def summarize_efficiency(run_dir: Path, per_case_names: list[str]) -> dict[str, Any]:
    entries = []
    tool_definition = None
    for case_name in per_case_names:
        case_dir = run_dir / case_name
        eff = load_optional_json(case_dir / "efficiency.json")
        if not eff:
            eff = infer_efficiency_from_artifacts(case_dir)
        status = load_optional_json(run_dir / case_name / "status.json")
        if not eff and not status:
            continue
        merged: dict[str, Any] = {}
        if eff:
            merged.update(eff)
        if status and "elapsed_seconds" in status and "elapsed_seconds" not in merged:
            merged["elapsed_seconds"] = status["elapsed_seconds"]
        merged["case_name"] = case_name
        if tool_definition is None and "tool_count_definition" in merged:
            tool_definition = merged["tool_count_definition"]
        entries.append(merged)

    if not entries:
        return {}

    def mean_for(key: str) -> float | None:
        values = [float(entry[key]) for entry in entries if key in entry]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    summary = {
        "tool_count_definition": tool_definition,
        "n_cases": len(entries),
        "mean_wall_seconds": mean_for("elapsed_seconds"),
        "mean_tools_per_task": mean_for("tool_calls"),
    }
    for key in (
        "mcp_calls",
        "read_calls",
        "grep_calls",
        "glob_calls",
        "write_calls",
        "edit_calls",
        "bash_calls",
        "assistant_messages",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "generated_file_events",
        "saved_file_events",
        "review_loops",
        "lint_checker_invocations",
        "retrieval_queries",
    ):
        mean_value = mean_for(key)
        if mean_value is not None:
            summary[f"mean_{key}_per_task"] = mean_value

    return summary


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
        run_dir = Path(path)
        quality = evaluate_agent_run(run_dir, manifest, gt_root)
        quality["efficiency"] = summarize_efficiency(
            run_dir,
            [case["case_name"] for case in manifest["cases"]],
        )
        results[label] = quality

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
