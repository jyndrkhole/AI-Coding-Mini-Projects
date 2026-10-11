from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.resource import ResourceListResponse, ResourceResponse
from app.services.resource_service import get_resource, list_resources

router = APIRouter(tags=["resources"])


@router.get("/resources", response_model=ResourceListResponse)
def resources(
    service: str | None = None,
    region: str | None = None,
    environment: str | None = None,
    state: str | None = None,
    tag: str | None = None,
    session: Session = Depends(get_db),
) -> ResourceListResponse:
    return ResourceListResponse(**list_resources(session, service, region, environment, state, tag))


@router.get("/resources/{resource_id:path}", response_model=ResourceResponse)
def resource_detail(resource_id: str, session: Session = Depends(get_db)) -> ResourceResponse:
    return ResourceResponse(**get_resource(session, resource_id))
