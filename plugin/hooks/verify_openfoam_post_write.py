#!/usr/bin/env python3
"""PostToolUse hook for immediate OpenFOAM dictionary validation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from openfoam_case_check import validate_openfoam_file


def _envflag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _workspace_root() -> Path:
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        return Path(project)
    return Path("/workspace")


def _inputs_dir() -> Path:
    override = os.environ.get("OPENFOAM_HOOK_INPUTS_DIR")
    if override:
        return Path(override)
    return _workspace_root() / "inputs"


def _allow() -> None:
    json.dump({"continue": True, "suppressOutput": True}, sys.stdout)
    sys.stdout.write("\n")
    sys.exit(0)


def _block(message: str) -> None:
    json.dump({"decision": "block", "reason": message}, sys.stdout)
    sys.stdout.write("\n")
    sys.exit(0)


def _collect_paths(payload: dict) -> list[Path]:
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool not in {"Write", "Edit", "MultiEdit"}:
        return []
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        return [Path(file_path)]
    return []


def main() -> None:
    if _envflag("OPENFOAM_HOOK_DISABLE"):
        _allow()

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        _allow()

    inputs_dir = _inputs_dir()
    paths = _collect_paths(payload)
    for raw in paths:
        try:
            path = raw.resolve()
        except OSError:
            continue
        try:
            inside = path.is_relative_to(inputs_dir.resolve())
        except (AttributeError, ValueError):
            inside = str(path).startswith(str(inputs_dir.resolve()))
        if not inside or not path.exists():
            continue
        issues = validate_openfoam_file(path, inputs_dir)
        blocking = [issue for issue in issues if issue.category != "decode_warning"]
        if blocking:
            _block(
                "PostToolUse OpenFOAM validation failed for "
                f"{path.relative_to(inputs_dir)}:\n"
                + "\n".join(f"- {issue.message}" for issue in blocking[:6])
            )

    _allow()


if __name__ == "__main__":
    main()
