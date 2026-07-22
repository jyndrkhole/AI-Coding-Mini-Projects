"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_services
from app.api.routes import emails, knowledge, misc, prompts, workspaces
from app.config import get_settings
from app.database.session import AsyncSessionLocal, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("email_ai")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.ensure_directories()
    await init_db()

    async with AsyncSessionLocal() as db:
        services = get_services()
        await services.workspace.ensure_default(db)
        await services.prompt.seed_builtins(db)
        await db.commit()

    logger.info("Email Intelligence Platform started")
    yield
    logger.info("Email Intelligence Platform stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Fully local AI-powered Email Intelligence Platform for CTOs and Solution Architects",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(emails.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(workspaces.router, prefix="/api")
    app.include_router(prompts.router, prefix="/api")
    app.include_router(misc.settings_router, prefix="/api")
    app.include_router(misc.style_router, prefix="/api")
    app.include_router(misc.chat_router, prefix="/api")
    app.include_router(misc.logs_router, prefix="/api")
    app.include_router(misc.dashboard_router, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
