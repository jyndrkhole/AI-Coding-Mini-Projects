import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database.connection import get_db
from app.database.models import Itinerary, User
from app.database.repositories.accounts import TripRepository, serialize_day, serialize_trip
from app.database.repositories.destinations import DestinationRepository, SavedRepository, serialize_destination
from app.services.itinerary import build_itinerary, regenerate_day

router = APIRouter(tags=["trips"])


class TripIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    origin: str = ""
    destination_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    traveler_count: int = Field(default=1, ge=1, le=20)
    adults: int = Field(default=1, ge=0, le=20)
    children: int = Field(default=0, ge=0, le=20)
    budget: float = Field(default=0, ge=0)
    status: str = "draft"


class GenerateIn(BaseModel):
    destination: str
    days: int = Field(ge=1, le=14)
    people: int = Field(default=2, ge=1, le=20)
    origin: str = ""
    budget: float = Field(default=0, ge=0)
    save: bool = True


class DayUpdate(BaseModel):
    title: str | None = None
    activities: dict | None = None
    estimated_cost: float | None = Field(default=None, ge=0)


def _owned_day(db: Session, day_id: int, user_id: int) -> Itinerary:
    day = db.get(Itinerary, day_id)
    if day is None or day.trip.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That itinerary day was not found."})
    return day


@router.get("/api/trips")
def list_trips(user: User = Depends(current_user), db: Session = Depends(get_db)):
    trips = TripRepository(db).list_for_user(user.id)
    return {"success": True, "data": [serialize_trip(trip) for trip in trips]}


@router.post("/api/trips", status_code=status.HTTP_201_CREATED)
def create_trip(body: TripIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = TripRepository(db).create(user.id, **body.model_dump())
    loaded = TripRepository(db).get_for_user(trip.id, user.id)
    return {"success": True, "data": serialize_trip(loaded)}


@router.get("/api/trips/{trip_id}")
def get_trip(trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    trip = TripRepository(db).get_for_user(trip_id, user.id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That trip was not found."})
    return {"success": True, "data": serialize_trip(trip)}


@router.put("/api/trips/{trip_id}")
def update_trip(trip_id: int, body: TripIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    repo = TripRepository(db)
    trip = repo.get_for_user(trip_id, user.id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That trip was not found."})
    repo.update(trip, **body.model_dump())
    return {"success": True, "data": serialize_trip(repo.get_for_user(trip_id, user.id))}


@router.post("/api/itineraries/generate")
def generate(body: GenerateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    repo = DestinationRepository(db)
    destination = repo.detail(body.destination)
    if destination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That destination is not in the catalogue."})
    try:
        days = build_itinerary(repo, destination, body.days)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "invalid", "message": str(exc)}) from exc
    if not body.save:
        return {"success": True, "data": {"days": days, "destination": destination.name}}
    trip = TripRepository(db).create(
        user.id,
        title=f"{destination.name} · {body.days} days",
        origin=body.origin,
        destination_id=destination.id,
        traveler_count=body.people,
        adults=body.people,
        children=0,
        budget=body.budget,
        status="planned",
    )
    TripRepository(db).replace_days(trip, days)
    loaded = TripRepository(db).get_for_user(trip.id, user.id)
    return {"success": True, "data": serialize_trip(loaded)}


@router.get("/api/itineraries/{day_id}")
def get_day(day_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"success": True, "data": serialize_day(_owned_day(db, day_id, user.id))}


@router.put("/api/itineraries/{day_id}")
def update_day(day_id: int, body: DayUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    day = _owned_day(db, day_id, user.id)
    if body.title:
        day.title = body.title
    if body.activities is not None:
        day.activities_json = json.dumps(body.activities)
    if body.estimated_cost is not None:
        day.estimated_cost = body.estimated_cost
    db.commit()
    db.refresh(day)
    return {"success": True, "data": serialize_day(day)}


@router.post("/api/itineraries/{day_id}/regenerate")
def regenerate(day_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    day = _owned_day(db, day_id, user.id)
    trip = day.trip
    if trip.destination_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "invalid", "message": "This trip has no destination."})
    repo = DestinationRepository(db)
    destination = repo.get(trip.destination_id)
    current = serialize_day(day)
    updated = regenerate_day(repo, destination, {"title": current["title"], "activities": current["activities"], "estimated_cost": current["estimated_cost"], "day_number": day.day_number})
    day.title = updated["title"]
    day.activities_json = json.dumps(updated["activities"])
    day.estimated_cost = updated["estimated_cost"]
    db.commit()
    db.refresh(day)
    return {"success": True, "data": serialize_day(day)}


@router.get("/api/me/saved")
def saved(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = SavedRepository(db).list_for_user(user.id)
    return {"success": True, "data": [serialize_destination(row, brief=True) for row in rows]}
