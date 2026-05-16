"""Background task runner — wraps the existing hybrid workflow."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .models import Task, get_task, update_task

logger = logging.getLogger("papercoder.runner")


async def run_paper_task(task: Task) -> None:
    """Execute the paper reproduction workflow in background, updating DB state."""
    task_id = task.id

    await update_task(task_id, status="running", current_node="document_analysis")

    try:
        # Import hybrid workflow (no changes to existing code)
        from ..hybrid.config import Settings
        from ..hybrid.logging_utils import setup_console_logging
        from ..hybrid.state import PaperState
        from ..hybrid.workflow import create_workflow

        setup_console_logging("info")

        output_root = Path(task.output_dir) if task.output_dir else Path("./output")
        base_settings = Settings(output_root=output_root)
        run_output_root = base_settings.create_run_output_root(Path(task.pdf_path))
        settings = Settings(
            output_root=run_output_root,
            log_dir_override=str(output_root / "logs"),
        )
        settings.ensure_dirs()

        workflow = create_workflow(settings)

        initial_state: PaperState = {
            "pdf_path": task.pdf_path,
            "iteration_count": 0,
            "max_iterations": task.max_iterations,
            "errors": [],
        }

        # Run in thread to avoid blocking event loop
        final_state = await asyncio.to_thread(
            workflow.invoke,
            initial_state,
            {"configurable": {"thread_id": task_id}},
        )

        # Map final state to DB fields
        passed = final_state.get("verification_passed", False)
        await update_task(
            task_id,
            status="passed" if passed else "failed",
            output_dir=str(settings.output_root),
            analysis_status=final_state.get("analysis_status", ""),
            generation_status=final_state.get("generation_status", ""),
            verification_passed=passed,
            iteration_count=final_state.get("iteration_count", 0),
            error_cause=final_state.get("error_cause", ""),
            error_type=final_state.get("error_type", ""),
            stdout_summary=final_state.get("stdout_summary", ""),
            repair_status=final_state.get("repair_status", ""),
            current_node="completed",
        )

    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        await update_task(
            task_id,
            status="failed",
            error_cause=str(exc),
            current_node="error",
        )