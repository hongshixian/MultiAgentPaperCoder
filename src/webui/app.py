"""FastAPI application entry point for DeepAgentsWebUI."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("papercoder.webui")

# Connected WebSocket clients (task_id → set of websockets)
ws_clients: dict[str, set[WebSocket]] = {}
ws_global: set[WebSocket] = set()


async def broadcast_task_update(task_id: str, data: dict) -> None:
    """Push task state update to all subscribed WebSocket clients."""
    dead: list[WebSocket] = []
    targets = ws_clients.get(task_id, set()) | ws_global
    for ws in targets:
        try:
            await ws.send_json({"type": "task_update", "task_id": task_id, **data})
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_global.discard(ws)
        for s in ws_clients.values():
            s.discard(ws)


async def start_task_execution(task) -> None:
    """Launch background task and push updates via WebSocket."""
    from .runner import run_paper_task
    from .models import Task

    task_obj = Task(**task) if isinstance(task, dict) else task
    asyncio.create_task(_run_with_ws_updates(task_obj))


async def _run_with_ws_updates(task: Task) -> None:
    from .runner import run_paper_task
    await run_paper_task(task)
    from .models import get_task
    updated = await get_task(task.id)
    if updated:
        await broadcast_task_update(task.id, updated)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .models import init_db
    await init_db()
    yield


app = FastAPI(title="MultiAgentPaperCoder WebUI", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/{task_id}")
async def ws_task(ws: WebSocket, task_id: str):
    await ws.accept()
    ws_clients.setdefault(task_id, set()).add(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive
    except WebSocketDisconnect:
        ws_clients[task_id].discard(ws)


@app.websocket("/ws")
async def ws_all(ws: WebSocket):
    await ws.accept()
    ws_global.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_global.discard(ws)


# Routes
from .routes import router as task_router  # noqa: E402
app.include_router(task_router)

# Static frontend
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)