from fastapi import APIRouter

from app.core.config import get_settings
from app.db.database import database_status
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    database = database_status()
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        service="aws-cost-guardian",
        version=settings.app_version,
        mock_aws=settings.mock_aws,
        database=database,
    )
