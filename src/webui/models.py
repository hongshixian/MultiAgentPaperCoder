"""Task model and SQLite persistence for the WebUI."""

from __future__ import annotations

import aiosqlite
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).parent.parent.parent / "webui_tasks.db"


@dataclass
class Task:
    id: str
    pdf_name: str
    pdf_path: str
    status: str  # pending | running | passed | failed
    max_iterations: int
    output_dir: str
    created_at: str

    # Workflow state snapshots
    current_node: str = ""
    analysis_status: str = ""
    generation_status: str = ""
    verification_passed: bool | None = None
    iteration_count: int = 0
    error_cause: str = ""
    error_type: str = ""
    stdout_summary: str = ""
    repair_status: str = ""

    @classmethod
    def new(cls, pdf_name: str, pdf_path: str, max_iterations: int = 5) -> Task:
        return cls(
            id=uuid4().hex[:12],
            pdf_name=pdf_name,
            pdf_path=pdf_path,
            status="pending",
            max_iterations=max_iterations,
            output_dir="",
            created_at=datetime.now(timezone.utc).isoformat(),
        )


async def init_db() -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                pdf_name TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                max_iterations INTEGER DEFAULT 5,
                output_dir TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                current_node TEXT DEFAULT '',
                analysis_status TEXT DEFAULT '',
                generation_status TEXT DEFAULT '',
                verification_passed INTEGER,
                iteration_count INTEGER DEFAULT 0,
                error_cause TEXT DEFAULT '',
                error_type TEXT DEFAULT '',
                stdout_summary TEXT DEFAULT '',
                repair_status TEXT DEFAULT ''
            )
        """)
        await db.commit()


async def create_task(task: Task) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """INSERT INTO tasks (id, pdf_name, pdf_path, status, max_iterations,
               output_dir, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task.id, task.pdf_name, task.pdf_path, task.status,
             task.max_iterations, task.output_dir, task.created_at),
        )
        await db.commit()


async def get_task(task_id: str) -> dict | None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_tasks() -> list[dict]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_task(task_id: str, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [task_id]
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(f"UPDATE tasks SET {sets} WHERE id = ?", values)
        await db.commit()