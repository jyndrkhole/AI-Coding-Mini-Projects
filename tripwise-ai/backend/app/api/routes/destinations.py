from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database.connection import get_db
from app.database.models import User
from app.database.repositories.destinations import (
    MONTHS,
    DestinationRepository,
    SavedRepository,
    serialize_destination,
    serialize_detail,
)

router = APIRouter(prefix="/api/destinations", tags=["destinations"])


@router.get("")
def list_destinations(
    q: str | None = None,
    destination_type: str | None = None,
    month: str | None = None,
    sort: str = "name",
    db: Session = Depends(get_db),
):
    month_number = MONTHS.get(month.strip().lower()) if month else None
    if month and month.strip().isdigit():
        month_number = int(month)
    repo = DestinationRepository(db)
    rows = repo.list(q=q, destination_type=destination_type, month=month_number, sort=sort)
    return {"success": True, "data": [serialize_destination(row, brief=True) for row in rows]}


@router.get("/search")
def search_destinations(q: str = "", db: Session = Depends(get_db)):
    repo = DestinationRepository(db)
    rows = repo.list(q=q)
    return {"success": True, "data": [serialize_destination(row, brief=True) for row in rows]}


@router.get("/links")
def links_from(origin: str = Query(...), max_hours: float | None = None, db: Session = Depends(get_db)):
    repo = DestinationRepository(db)
    found = []
    for link in repo.links_from(origin, max_hours=max_hours):
        destination = repo.get(link.destination_id)
        if destination is None:
            continue
        found.append(
            {
                "origin": link.origin_city,
                "typical_hours": float(link.typical_hours),
                "typical_cost_per_person": float(link.typical_cost_per_person),
                "mode": link.mode,
                "notes": link.notes,
                "price_label": "demonstration_estimate",
                "destination": serialize_destination(destination, brief=True),
            }
        )
    return {"success": True, "data": found}


@router.get("/{key}")
def destination_detail(key: str, db: Session = Depends(get_db)):
    repo = DestinationRepository(db)
    destination = repo.detail(key)
    if destination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That destination is not in the catalogue."})
    return {"success": True, "data": serialize_detail(repo, destination)}


@router.post("/{destination_id}/save")
def save_destination(destination_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if DestinationRepository(db).get(destination_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That destination is not in the catalogue."})
    SavedRepository(db).add(user.id, destination_id)
    return {"success": True, "data": {"saved": True}}


@router.delete("/{destination_id}/save")
def unsave_destination(destination_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    SavedRepository(db).remove(user.id, destination_id)
    return {"success": True, "data": {"saved": False}}
