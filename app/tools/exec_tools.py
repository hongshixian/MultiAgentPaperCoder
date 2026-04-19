"""Deterministic verification tools."""

from __future__ import annotations

import logging
import py_compile
import subprocess
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


def run_python_entrypoint(root_dir: str, entrypoint: str = "main.py", timeout_seconds: int = 30) -> str:
    """Run the generated Python entrypoint and capture stdout/stderr."""
    project_root = Path(root_dir)
    entrypoint_path = project_root / entrypoint
    if not entrypoint_path.exists():
        logger.warning("Cannot run missing entrypoint: %s", entrypoint_path)
        return f"NOT_RUN\nMissing entrypoint: {entrypoint_path}"

    try:
        completed = subprocess.run(
            ["python", entrypoint],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or "").strip()
        logger.warning("Entrypoint timed out after %ss: %s", timeout_seconds, entrypoint_path)
        return (
            f"TIMEOUT\n"
            f"Command: python {entrypoint}\n"
            f"Timeout: {timeout_seconds}s\n"
            f"STDOUT:\n{stdout or '(empty)'}\n\n"
            f"STDERR:\n{stderr or '(empty)'}"
        )

    status = "PASSED" if completed.returncode == 0 else "FAILED"
    logger.info("Entrypoint run %s for %s with exit code %d", status, entrypoint_path, completed.returncode)
    return (
        f"{status}\n"
        f"Command: python {entrypoint}\n"
        f"Exit Code: {completed.returncode}\n"
        f"STDOUT:\n{completed.stdout.strip() or '(empty)'}\n\n"
        f"STDERR:\n{completed.stderr.strip() or '(empty)'}"
    )
