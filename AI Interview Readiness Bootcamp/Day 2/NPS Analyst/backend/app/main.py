"""NPS Analyst API. Numeric routes stay available when no model key is configured."""

from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import agents, health, overview, reports, revenue_risk, surveys, themes
from app.core.logging import configure_logging
from app.db.database import init_db, reset_engine, session_factory
from app.services import analysis_service, survey_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    app.state.session_factory = session_factory()
    app.state.dataset_id = None
    app.state.load_error = None
    session = app.state.session_factory()
    try:
        dataset_id = survey_service.ensure_default(session)
        app.state.dataset_id = dataset_id
        if dataset_id is None:
            app.state.load_error = "The default survey file was not found. Upload a CSV. No rows were invented."
        elif os.environ.get("NPS_SKIP_AUTO_ANALYSIS") != "1":
            await analysis_service.run_analysis(session, dataset_id)
    except Exception:
        logger.exception("startup failed")
        app.state.load_error = "The survey could not be loaded. Check the file and the API log."
    finally:
        session.close()
    yield


def create_app() -> FastAPI:
    reset_engine()
    app = FastAPI(title="NPS Analyst in a Box", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (health, surveys, overview, themes, revenue_risk, agents, reports):
        app.include_router(module.router)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        if isinstance(exc, RequestValidationError):
            return await request_validation_exception_handler(request, exc)
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        logger.error("request failed: %s", exc.__class__.__name__)
        return JSONResponse(status_code=500, content={"detail": "The request could not be completed."})

    return app


app = create_app()
