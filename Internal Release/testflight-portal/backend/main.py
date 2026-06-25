"""AgentVizion2Go Release Portal — FastAPI server."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings
from groq_agent import analyze_logs
from pipeline import ReleaseTarget, pipeline

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="AgentVizion2Go Release Portal", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReleaseRequest(BaseModel):
    platform: ReleaseTarget


class AnalyzeRequest(BaseModel):
    question: str | None = None


class AnalyzeResponse(BaseModel):
    analysis: str


def _validate_release(target: ReleaseTarget) -> None:
    if target in ("ios", "both") and not (
        settings.apple_id and settings.apple_app_password
    ):
        raise HTTPException(
            status_code=400,
            detail="Apple credentials missing. Set APPLE_ID and APPLE_APP_PASSWORD in .env",
        )

    if target in ("android", "both") and not settings.android_configured:
        raise HTTPException(
            status_code=400,
            detail="Android signing config missing. Check .env keystore settings.",
        )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "groq_configured": bool(settings.groq_api_key),
        "apple_configured": bool(settings.apple_id and settings.apple_app_password),
        "android_configured": settings.android_configured,
        "android_keystore_exists": settings.android_keystore_path.exists(),
    }


@app.get("/api/preview")
async def preview():
    from pipeline import get_current_build_preview

    return await get_current_build_preview()


@app.get("/api/status")
async def status():
    return pipeline.status()


@app.post("/api/release")
async def start_release(request: ReleaseRequest):
    _validate_release(request.platform)

    try:
        started = await pipeline.start(request.platform)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "message": "Release started",
        "platform": request.platform,
        "started": started,
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    logs = "\n".join(pipeline.combined_logs)
    if not logs:
        raise HTTPException(status_code=400, detail="No logs available yet")
    analysis = await analyze_logs(logs, request.question)
    return AnalyzeResponse(analysis=analysis)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue[str] = asyncio.Queue()

    def on_log(line: str) -> None:
        try:
            queue.put_nowait(line)
        except asyncio.QueueFull:
            pass

    pipeline.subscribe_logs(on_log)

    try:
        for line in pipeline.combined_logs:
            await websocket.send_text(line)

        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(line)
            except asyncio.TimeoutError:
                await websocket.send_text("__ping__")
    except WebSocketDisconnect:
        pass
    finally:
        if on_log in pipeline._log_callbacks:
            pipeline._log_callbacks.remove(on_log)


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
