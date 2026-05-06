# /// script
# dependencies = [
#   "mcp>=1.0.0,<2",
# ]
# ///
"""MCP server exposing OpenFOAM case validation as an agent-callable tool."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", HERE.parents[1]))
HOOKS_DIR = PLUGIN_ROOT / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from openfoam_case_check import (
    ValidationIssue,
    validate_case,
    validate_openfoam_file as validate_openfoam_file_impl,
)


mcp = FastMCP("openfoam-validate")


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


def _resolve(path_str: str) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate
    inputs_dir = _inputs_dir()
    workspace_root = _workspace_root()
    for path in (Path.cwd() / candidate, workspace_root / candidate, inputs_dir / candidate):
        if path.exists():
            return path
    return inputs_dir / candidate


def _format_issues(issues: list[ValidationIssue]) -> str:
    return "\n".join(f"- [{issue.category}] {issue.message}" for issue in issues)


@mcp.tool()
def validate_openfoam_case() -> str:
    """Validate all generated OpenFOAM case files under `/workspace/inputs`.

    Use this before finishing your turn when you have written or edited case
    files. It checks that required task files exist, that OpenFOAM dictionary
    delimiters are balanced, and that key files contain the expected sections.
    """
    inputs_dir = _inputs_dir()
    workspace_root = _workspace_root()
    issues = validate_case(inputs_dir=inputs_dir, workspace_root=workspace_root)
    if not issues:
        return f"{inputs_dir}: validation passed"
    return f"{inputs_dir}: validation failed\n{_format_issues(issues)}"


@mcp.tool()
def validate_openfoam_file(file_path: str) -> str:
    """Validate a single generated OpenFOAM file.

    Args:
        file_path: Absolute path, or a path relative to `/workspace` or
            `/workspace/inputs`.
    """
    inputs_dir = _inputs_dir()
    target = _resolve(file_path)
    if not target.exists():
        return f"ERROR: file not found: {target} (resolved from {file_path!r})"
    try:
        rel = target.relative_to(inputs_dir)
    except ValueError:
        return (
            f"ERROR: {target} is outside the generated case directory {inputs_dir}. "
            "Only validate files under /workspace/inputs."
        )
    issues = validate_openfoam_file_impl(target, inputs_dir)
    if not issues:
        return f"{rel}: validation passed"
    return f"{rel}: validation failed\n{_format_issues(issues)}"


if __name__ == "__main__":
    mcp.run()
