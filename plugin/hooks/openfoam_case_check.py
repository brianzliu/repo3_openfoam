from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationIssue:
    category: str
    message: str


def load_task_manifest(workspace_root: Path) -> dict | None:
    manifest_path = workspace_root / "task_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def list_case_files(inputs_dir: Path) -> list[Path]:
    if not inputs_dir.exists():
        return []
    return sorted(path for path in inputs_dir.rglob("*") if path.is_file())


def _balanced_pairs(text: str, left: str, right: str) -> bool:
    depth = 0
    for char in text:
        if char == left:
            depth += 1
        elif char == right:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def validate_openfoam_file(path: Path, inputs_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
        issues.append(
            ValidationIssue(
                "decode_warning",
                f"{path.relative_to(inputs_dir)} could not be decoded cleanly as UTF-8",
            )
        )
    rel = path.relative_to(inputs_dir)
    stripped = text.strip()
    if not stripped:
        issues.append(ValidationIssue("empty_file", f"{rel} is empty"))
        return issues

    for left, right, label in [("{", "}", "braces"), ("(", ")", "parens"), ("[", "]", "brackets")]:
        if not _balanced_pairs(stripped, left, right):
            issues.append(ValidationIssue("unbalanced", f"{rel} has unbalanced {label}"))

    if "FoamFile" not in text and rel.suffix not in {".sh", ".py"}:
        issues.append(
            ValidationIssue(
                "missing_header",
                f"{rel} is missing a FoamFile header block",
            )
        )

    leaf_like = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("//", "/*", "*"))
    ]
    for line in leaf_like:
        if line.endswith(("{", "}", "(", ")", ";")):
            continue
        if line.startswith("#"):
            continue
        if line in {"FoamFile"}:
            continue
        if "{" not in line and "}" not in line:
            issues.append(
                ValidationIssue(
                    "missing_terminator",
                    f"{rel} contains a line without an obvious dictionary terminator: {line[:120]}",
                )
            )
            break

    rel_text = rel.as_posix()
    if rel_text == "system/blockMeshDict":
        for token in ("vertices", "blocks", "boundary"):
            if token not in text:
                issues.append(
                    ValidationIssue(
                        "blockmesh_missing_section",
                        f"{rel} is missing `{token}`",
                    )
                )
    if rel_text == "system/fvSchemes":
        for token in ("ddtSchemes", "divSchemes"):
            if token not in text:
                issues.append(
                    ValidationIssue("fvschemes_missing_section", f"{rel} is missing `{token}`")
                )
    if rel_text == "system/fvSolution" and "solvers" not in text:
        issues.append(ValidationIssue("fvsolution_missing_solvers", f"{rel} is missing `solvers`"))
    if rel.parts and rel.parts[0] == "0":
        for token in ("dimensions", "internalField", "boundaryField"):
            if token not in text:
                issues.append(
                    ValidationIssue("field_missing_section", f"{rel} is missing `{token}`")
                )

    return issues


def validate_case(inputs_dir: Path, workspace_root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    manifest = load_task_manifest(workspace_root)
    files = list_case_files(inputs_dir)
    if not files:
        issues.append(
            ValidationIssue("no_outputs", f"No files found under {inputs_dir}")
        )
        return issues

    if manifest:
        required = manifest.get("required_files", [])
        for rel in required:
            if not (inputs_dir / rel).exists():
                issues.append(
                    ValidationIssue(
                        "missing_required_file",
                        f"Missing required file: {rel}",
                    )
                )

    for path in files:
        issues.extend(validate_openfoam_file(path, inputs_dir))

    return issues
