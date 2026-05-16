"""FastAPI application entry point for DeepAgentsWebUI."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MultiAgentPaperCoder WebUI")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)