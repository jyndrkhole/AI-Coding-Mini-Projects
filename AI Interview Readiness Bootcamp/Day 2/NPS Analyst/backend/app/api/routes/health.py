from fastapi import APIRouter, Request

from app.core.config import llm_configured

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "deterministic_only": not llm_configured(),
        "llm_configured": llm_configured(),
        "dataset_loaded": bool(getattr(request.app.state, "dataset_id", None)),
        "load_error": getattr(request.app.state, "load_error", None),
        "fictional_data": True,
    }
