"""Filesystem tools for storing artifacts and generated code."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("papercoder.tools.artifacts")


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _output_root() -> Path:
    return Path(os.getenv("OUTPUT_ROOT", "./output")).resolve()


def _resolve_under(root: Path, target: str) -> Path:
    path = Path(target)
    if not path.is_absolute():
        path = (_workspace_root() / path).resolve()
    else:
        path = path.resolve()

    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path must stay under {root}: {path}") from exc

    return path


def _resolve_under_any(roots: list[Path], target: str) -> Path:
    last_error: ValueError | None = None
    for root in roots:
        try:
            return _resolve_under(root, target)
        except ValueError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def save_text_file(path: str, content: str) -> str:
    """Save a text file under OUTPUT_ROOT."""
    file_path = _resolve_under(_output_root(), path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    logger.info("Saved text file %s (%d chars)", file_path, len(content))
    return f"saved: {file_path}"


def read_text_file(path: str) -> str:
    """Read a text file under the current workspace."""
    file_path = _resolve_under_any([_workspace_root(), _output_root()], path)
    if not file_path.exists():
        logger.error("File not found for read_text_file: %s", path)
        raise FileNotFoundError(f"File not found: {path}")
    logger.info("Reading text file %s", file_path)
    return file_path.read_text(encoding="utf-8")


def list_files(root_dir: str) -> str:
    """List files under a workspace-relative directory."""
    root = _resolve_under_any([_workspace_root(), _output_root()], root_dir)
    if not root.exists():
        logger.info("Listing files under %s returned empty because directory is missing", root)
        return ""
    files = [str(path) for path in root.rglob("*") if path.is_file()]
    logger.info("Listed %d files under %s", len(files), root)
    return "\n".join(sorted(files))
