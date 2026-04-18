"""Deterministic verification tools."""

from __future__ import annotations

import py_compile
from pathlib import Path


def python_syntax_check(root_dir: str) -> str:
    """Compile every Python file below root_dir."""
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    checked: list[str] = []
    errors: list[str] = []

    for file_path in root.rglob("*.py"):
        try:
            py_compile.compile(str(file_path), doraise=True)
            checked.append(str(file_path))
        except py_compile.PyCompileError as exc:
            errors.append(f"{file_path}: {exc.msg}")

    if errors:
        return "FAILED\n" + "\n".join(errors)

    return "PASSED\n" + "\n".join(checked)


def check_entrypoint_exists(root_dir: str, entrypoint: str = "main.py") -> str:
    """Check whether a Python entrypoint exists in the generated project."""
    path = Path(root_dir) / entrypoint
    if path.exists():
        return f"FOUND: {path}"
    return f"MISSING: {path}"
