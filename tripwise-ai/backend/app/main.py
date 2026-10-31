"""TripWise API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.vector_store import collection_count
from app.api.routes import admin, advisor, auth, budget, destinations, trips
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.connection import SessionLocal, init_db
from app.mcp.client import open_session
from app.services.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="TripWise AI", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": detail})


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "status": "ok",
            "database": "ok",
            "chroma_documents": collection_count(),
            "llm_configured": settings.llm_configured,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.groq_model if settings.llm_provider == "groq" else settings.openai_model,
        },
    }


@app.get("/api/mcp/status")
async def mcp_status():
    async with open_session() as session:
        tools = (await session.list_tools()).tools
        resources = (await session.list_resources()).resources
        templates = (await session.list_resource_templates()).resourceTemplates
        prompts = (await session.list_prompts()).prompts
    return {
        "success": True,
        "data": {
            "server": "TripWise Server",
            "tools": [tool.name for tool in tools],
            "resources": [str(item.uri) for item in resources],
            "resource_templates": [str(item.uriTemplate) for item in templates],
            "prompts": [item.name for item in prompts],
        },
    }


app.include_router(auth.router)
app.include_router(destinations.router)
app.include_router(advisor.router)
app.include_router(budget.router)
app.include_router(trips.router)
app.include_router(admin.router)
