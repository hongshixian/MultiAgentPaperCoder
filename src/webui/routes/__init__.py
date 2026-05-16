"""REST API routes for task management."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ..models import Task, create_task, get_task, list_tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"


@router.get("")
async def api_list_tasks():
    return await list_tasks()


@router.get("/{task_id}")
async def api_get_task(task_id: str):
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("")
async def api_create_task(
    pdf: UploadFile = File(...),
    max_iterations: int = Form(5),
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    task = Task.new(pdf_name=pdf.filename or "unknown.pdf", pdf_path="",
                    max_iterations=max_iterations)

    # Save uploaded PDF
    pdf_path = UPLOAD_DIR / f"{task.id}_{pdf.filename}"
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf.file, f)
    task.pdf_path = str(pdf_path.resolve())

    await create_task(task)

    # Schedule background execution (import here to avoid circular)
    from ..app import start_task_execution
    await start_task_execution(task)

    return {"id": task.id, "status": "running"}


@router.get("/{task_id}/output")
async def api_task_output(task_id: str):
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    output_dir = Path(task["output_dir"])
    if not output_dir.exists():
        return {"files": []}
    files = []
    for f in output_dir.rglob("*"):
        if f.is_file():
            files.append({
                "name": str(f.relative_to(output_dir)),
                "size": f.stat().st_size,
            })
    return {"files": files[:50]}