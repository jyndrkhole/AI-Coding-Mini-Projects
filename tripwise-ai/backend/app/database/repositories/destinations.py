"""Parameterized destination lookups. Tools call these methods and never send raw SQL."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.models import (
    Accommodation,
    Attraction,
    Destination,
    DestinationNearby,
    SavedDestination,
    TravelLink,
    TravelTip,
)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def money(value) -> float:
    return float(value)


class DestinationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        q: str | None = None,
        destination_type: str | None = None,
        month: int | None = None,
        sort: str = "name",
    ) -> list[Destination]:
        stmt = select(Destination)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Destination.name.ilike(like),
                    Destination.state.ilike(like),
                    Destination.destination_type.ilike(like),
                    Destination.description.ilike(like),
                    Destination.best_season.ilike(like),
                )
            )
        if destination_type:
            stmt = stmt.where(Destination.destination_type.ilike(destination_type.strip()))
        if sort == "budget":
            stmt = stmt.order_by(Destination.budget_min)
        elif sort == "duration":
            stmt = stmt.order_by(Destination.ideal_duration_days)
        else:
            stmt = stmt.order_by(Destination.name)
        rows = list(self.db.scalars(stmt))
        if month:
            rows = [row for row in rows if _month_matches(row.best_months, month)]
        return rows

    def get(self, destination_id: int) -> Destination | None:
        stmt = (
            select(Destination)
            .where(Destination.id == destination_id)
            .options(
                selectinload(Destination.accommodations),
                selectinload(Destination.attractions),
                selectinload(Destination.tips),
            )
        )
        return self.db.scalars(stmt).first()

    def by_code(self, code: str) -> Destination | None:
        stmt = select(Destination).where(Destination.code.ilike(code.strip()))
        return self.db.scalars(stmt).first()

    def by_slug(self, slug: str) -> Destination | None:
        stmt = select(Destination).where(Destination.slug == slug.strip().lower())
        return self.db.scalars(stmt).first()

    def by_name(self, name: str) -> Destination | None:
        key = name.strip().lower()
        stmt = select(Destination).where(Destination.name.ilike(key))
        found = self.db.scalars(stmt).first()
        if found:
            return found
        coded = self.by_code(key)
        if coded:
            return coded
        stmt = select(Destination).where(Destination.slug == key.replace(" ", "-"))
        return self.db.scalars(stmt).first()

    def detail(self, key: str) -> Destination | None:
        if key.isdigit():
            return self.get(int(key))
        found = self.by_code(key) or self.by_slug(key) or self.by_name(key)
        if not found:
            return None
        return self.get(found.id)

    def stays(self, destination_id: int) -> list[Accommodation]:
        stmt = (
            select(Accommodation)
            .where(Accommodation.destination_id == destination_id)
            .order_by(Accommodation.price_per_night)
        )
        return list(self.db.scalars(stmt))

    def attractions(self, destination_id: int) -> list[Attraction]:
        stmt = (
            select(Attraction)
            .where(Attraction.destination_id == destination_id)
            .order_by(Attraction.sequence_order, Attraction.id)
        )
        return list(self.db.scalars(stmt))

    def tips(
        self,
        destination_id: int | None = None,
        category: str | None = None,
        season: str | None = None,
    ) -> list[TravelTip]:
        stmt = select(TravelTip)
        if destination_id is None:
            stmt = stmt.where(TravelTip.destination_id.is_(None))
        else:
            stmt = stmt.where(
                or_(TravelTip.destination_id == destination_id, TravelTip.destination_id.is_(None))
            )
        if category:
            stmt = stmt.where(TravelTip.category == category)
        rows = list(self.db.scalars(stmt.order_by(TravelTip.id)))
        if season and season != "any":
            season_key = season.lower()
            rows = [row for row in rows if row.season.lower() in {season_key, "any"}]
        return rows

    def links_from(self, origin: str, max_hours: float | None = None) -> list[TravelLink]:
        stmt = select(TravelLink).where(TravelLink.origin_city.ilike(origin.strip()))
        rows = list(self.db.scalars(stmt))
        if max_hours is not None:
            rows = [row for row in rows if float(row.typical_hours) <= max_hours]
        return sorted(rows, key=lambda row: float(row.typical_hours))

    def link(self, origin: str, destination_id: int) -> TravelLink | None:
        stmt = select(TravelLink).where(
            TravelLink.origin_city.ilike(origin.strip()),
            TravelLink.destination_id == destination_id,
        )
        return self.db.scalars(stmt).first()

    def nearby(self, destination_id: int) -> list[tuple[Destination, str]]:
        stmt = select(DestinationNearby).where(DestinationNearby.destination_id == destination_id)
        pairs = []
        for link in self.db.scalars(stmt):
            other = self.db.get(Destination, link.nearby_id)
            if other:
                pairs.append((other, link.note))
        return pairs

    def representative_stay(self, destination_id: int) -> Accommodation | None:
        stays = self.stays(destination_id)
        return stays[0] if stays else None


def _month_matches(best_months: str, month: int) -> bool:
    parts = [part.strip() for part in (best_months or "").split(",") if part.strip()]
    return str(month) in parts


def serialize_destination(destination: Destination, brief: bool = False) -> dict:
    payload = {
        "id": destination.id,
        "name": destination.name,
        "slug": destination.slug,
        "code": destination.code,
        "travel_mode": destination.travel_mode,
        "country": destination.country,
        "state": destination.state,
        "description": destination.description,
        "destination_type": destination.destination_type,
        "best_season": destination.best_season,
        "best_months": destination.best_months,
        "ideal_duration_days": destination.ideal_duration_days,
        "budget_min": money(destination.budget_min),
        "budget_max": money(destination.budget_max),
        "family_fit": destination.family_fit,
        "couple_fit": destination.couple_fit,
        "adventure_fit": destination.adventure_fit,
        "image_url": destination.image_url,
        "price_label": "demonstration_estimate",
    }
    if brief:
        return payload
    payload.update(
        {
            "pros": destination.pros,
            "cons": destination.cons,
            "demo_travel_cost_per_person": money(destination.demo_travel_cost_per_person),
            "demo_daily_spend_per_person": money(destination.demo_daily_spend_per_person),
        }
    )
    return payload


def serialize_detail(repo: DestinationRepository, destination: Destination) -> dict:
    payload = serialize_destination(destination)
    payload["accommodations"] = [
        {
            "id": stay.id,
            "name": stay.name,
            "accommodation_type": stay.accommodation_type,
            "description": stay.description,
            "price_per_night": money(stay.price_per_night),
            "capacity": stay.capacity,
            "amenities": stay.amenities,
            "source": stay.source,
            "price_label": "demonstration_estimate",
        }
        for stay in repo.stays(destination.id)
    ]
    payload["attractions"] = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "category": item.category,
            "estimated_cost": money(item.estimated_cost),
            "ideal_duration": item.ideal_duration,
            "best_time_to_visit": item.best_time_to_visit,
            "sequence_order": item.sequence_order,
            "price_label": "demonstration_estimate",
        }
        for item in repo.attractions(destination.id)
    ]
    payload["tips"] = [
        {
            "id": tip.id,
            "category": tip.category,
            "title": tip.title,
            "content": tip.content,
            "season": tip.season,
            "source": tip.source,
        }
        for tip in repo.tips(destination.id)
    ]
    payload["nearby"] = [
        {"id": other.id, "name": other.name, "slug": other.slug, "note": note}
        for other, note in repo.nearby(destination.id)
    ]
    return payload


class SavedRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: int) -> list[Destination]:
        stmt = (
            select(Destination)
            .join(SavedDestination, SavedDestination.destination_id == Destination.id)
            .where(SavedDestination.user_id == user_id)
            .order_by(Destination.name)
        )
        return list(self.db.scalars(stmt))

    def add(self, user_id: int, destination_id: int) -> None:
        existing = self.db.scalars(
            select(SavedDestination).where(
                SavedDestination.user_id == user_id,
                SavedDestination.destination_id == destination_id,
            )
        ).first()
        if existing:
            return
        self.db.add(SavedDestination(user_id=user_id, destination_id=destination_id))
        self.db.commit()

    def remove(self, user_id: int, destination_id: int) -> None:
        row = self.db.scalars(
            select(SavedDestination).where(
                SavedDestination.user_id == user_id,
                SavedDestination.destination_id == destination_id,
            )
        ).first()
        if row:
            self.db.delete(row)
            self.db.commit()
