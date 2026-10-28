"""FastAPI entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.data.yfinance_provider import YFinanceProvider
from app.llm import LLMClient
from app.storage.db import AnalysisStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

settings = get_settings()
store = AnalysisStore(settings.database_path)
llm = LLMClient(settings)
provider = YFinanceProvider(settings.cache_ttl_seconds)

from app.agents.orchestrator import Orchestrator  # noqa: E402

orchestrator = Orchestrator(provider, llm, store, settings)

app = FastAPI(title="Fundamental Analyser", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
