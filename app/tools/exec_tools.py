"""Deterministic verification tools."""

from __future__ import annotations

import logging
import py_compile
from pathlib import Path

logger = logging.getLogger("papercoder.tools.exec")


def python_syntax_check(root_dir: str) -> str:
    """Compile every Python file below root_dir."""
    root = Path(root_dir)
    if not root.exists():
        logger.error("Syntax check root does not exist: %s", root_dir)
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
        logger.warning("Syntax check failed for %s with %d errors", root, len(errors))
        return "FAILED\n" + "\n".join(errors)

    logger.info("Syntax check passed for %s with %d files", root, len(checked))
    return "PASSED\n" + "\n".join(checked)


def check_entrypoint_exists(root_dir: str, entrypoint: str = "main.py") -> str:
    """Check whether a Python entrypoint exists in the generated project."""
    path = Path(root_dir) / entrypoint
    if path.exists():
        logger.info("Entrypoint found: %s", path)
        return f"FOUND: {path}"
    logger.warning("Entrypoint missing: %s", path)
    return f"MISSING: {path}"
