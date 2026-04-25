"""Logging helpers for the hybrid implementation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


def create_run_logger(log_dir: Path) -> tuple[logging.Logger, logging.Handler, Path, str]:
    """Create a dedicated file logger for a single run."""
    log_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"agent_run_{run_id}.log"

    logger = logging.getLogger(f"papercoder.run.{run_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger, handler, log_path, run_id


def serialize_for_log(value: Any) -> str:
    """Serialize a value for log output."""
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        return repr(value)
