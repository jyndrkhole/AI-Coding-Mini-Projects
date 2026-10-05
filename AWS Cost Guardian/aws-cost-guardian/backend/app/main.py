"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import aws, costs, health, recommendations, savings
from app.core.config import get_settings
from app.core.exceptions import FinOpsError
from app.core.logging import configure_logging
from app.db.database import init_db
from app.db.seed import seed_mock_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    if get_settings().mock_aws:
        seed_mock_data()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    for route in (health, aws, costs, recommendations, savings):
        app.include_router(route.router, prefix="/api")

    @app.exception_handler(FinOpsError)
    async def finops_error_handler(request: Request, exc: FinOpsError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    return app


app = create_app()
