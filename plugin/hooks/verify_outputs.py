#!/usr/bin/env python3
"""Stop-hook validation for OpenFOAM case authoring tasks."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from openfoam_case_check import ValidationIssue, validate_case


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


def format_issues(issues: list[ValidationIssue], limit: int = 8) -> str:
    lines = [f"- {issue.message}" for issue in issues[:limit]]
    if len(issues) > limit:
        lines.append(f"- ... plus {len(issues) - limit} more issue(s)")
    return "\n".join(lines)


def main() -> None:
    if _envflag("OPENFOAM_HOOK_DISABLE"):
        _allow()

    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        _allow()

    workspace_root = _workspace_root()
    inputs_dir = _inputs_dir()
    issues = validate_case(inputs_dir=inputs_dir, workspace_root=workspace_root)
    if not issues:
        _allow()

    _block(
        "Stop blocked by OpenFOAM verification hook. Fix the case files under "
        f"{inputs_dir} before ending the turn.\n\n{format_issues(issues)}"
    )


if __name__ == "__main__":
    main()
