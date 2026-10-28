"""HTTP API for a single-ticker fundamental analysis."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.data.errors import ProviderError, TickerNotFound
from app.domain.models import AnalyzeRequest

router = APIRouter(prefix="/api")


def _orchestrator():
    from app.main import orchestrator

    return orchestrator


@router.get("/status")
def status():
    from app.main import llm, settings

    info = settings.llm_status()
    return {
        "data_provider": "yfinance",
        "llm_provider": info["provider"],
        "llm_model": info["model"],
        "llm_configured": info["configured"],
        "llm_message": info["message"],
    }


@router.get("/reports")
async def list_reports():
    from app.main import store

    return await asyncio.to_thread(store.list_recent)


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    from app.main import store

    report = await asyncio.to_thread(store.get, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No saved report with that id.")
    return report


@router.post("/analyze")
async def analyze(body: AnalyzeRequest):
    try:
        return await _orchestrator().analyze(body)
    except TickerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/analyze/stream")
async def analyze_stream(body: AnalyzeRequest):
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event: dict) -> None:
        await queue.put(event)

    async def run() -> None:
        try:
            report = await _orchestrator().analyze(body, on_event=on_event)
            await queue.put({"type": "report", "report": json.loads(report.model_dump_json())})
        except TickerNotFound as exc:
            await queue.put({"type": "error", "status": 404, "detail": str(exc)})
        except ProviderError as exc:
            await queue.put({"type": "error", "status": 502, "detail": str(exc)})
        except Exception as exc:
            await queue.put({"type": "error", "status": 500, "detail": str(exc)})
        finally:
            await queue.put(None)

    task = asyncio.create_task(run())

    async def events():
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(events(), media_type="text/event-stream")
