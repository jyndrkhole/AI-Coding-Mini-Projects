"""Load the demonstration catalogue once. Safe to run on every startup."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.models import (
    Accommodation,
    Attraction,
    Destination,
    DestinationNearby,
    TravelLink,
    TravelTip,
    User,
)
from app.services.seed_data import DESTINATIONS, GENERAL_TIPS, NEARBY, SOURCE, TRAVEL_LINKS


def _slug(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def seed_if_empty(db: Session) -> None:
    _ensure_users(db)
    existing = db.scalar(select(func.count()).select_from(Destination)) or 0
    if existing:
        return
    codes: dict[str, Destination] = {}
    for item in DESTINATIONS:
        destination = Destination(
            code=item["code"],
            name=item["name"],
            slug=_slug(item["name"]),
            country="India",
            state=item["state"],
            description=item["description"],
            destination_type=item["destination_type"],
            best_season=item["best_season"],
            best_months=item["best_months"],
            ideal_duration_days=item["ideal_duration_days"],
            budget_min=item["budget_min"],
            budget_max=item["budget_max"],
            travel_mode=item["travel_mode"],
            demo_travel_cost_per_person=item["demo_travel_cost_per_person"],
            demo_daily_spend_per_person=item["demo_daily_spend_per_person"],
            family_fit=item["family_fit"],
            couple_fit=item["couple_fit"],
            adventure_fit=item["adventure_fit"],
            pros=item["pros"],
            cons=item["cons"],
            image_url=item["image_url"],
        )
        db.add(destination)
        db.flush()
        codes[item["code"]] = destination
        stay_name, stay_type, price, stay_description = item["stay"]
        db.add(
            Accommodation(
                destination_id=destination.id,
                name=stay_name,
                accommodation_type=stay_type,
                description=stay_description,
                price_per_night=price,
                capacity=2,
                amenities="Sample listing",
                source=SOURCE,
            )
        )
        for name, description, category, cost, duration, when, order in item["attractions"]:
            db.add(
                Attraction(
                    destination_id=destination.id,
                    name=name,
                    description=description,
                    category=category,
                    estimated_cost=cost,
                    ideal_duration=duration,
                    best_time_to_visit=when,
                    sequence_order=order,
                )
            )
        for category, title, content, season in item["tips"]:
            db.add(
                TravelTip(
                    destination_id=destination.id,
                    category=category,
                    title=title,
                    content=content,
                    season=season,
                    source=SOURCE,
                )
            )
    for category, title, content, season in GENERAL_TIPS:
        db.add(TravelTip(destination_id=None, category=category, title=title, content=content, season=season, source=SOURCE))
    for origin, code, hours, cost, mode, notes in TRAVEL_LINKS:
        db.add(
            TravelLink(
                origin_city=origin,
                destination_id=codes[code].id,
                typical_hours=hours,
                typical_cost_per_person=cost,
                mode=mode,
                notes=notes,
            )
        )
    for left, right, note in NEARBY:
        db.add(DestinationNearby(destination_id=codes[left].id, nearby_id=codes[right].id, note=note))
        db.add(DestinationNearby(destination_id=codes[right].id, nearby_id=codes[left].id, note=note))
    db.commit()


def _ensure_users(db: Session) -> None:
    demo = [
        ("Asha Traveller", "traveler@example.com", "Tripwise#Travel1", "user"),
        ("Admin", "admin@example.com", "Tripwise#Admin1", "admin"),
    ]
    changed = False
    for name, email, password, role in demo:
        found = db.scalar(select(User).where(User.email == email))
        if found:
            continue
        db.add(User(name=name, email=email, password_hash=hash_password(password), role=role))
        changed = True
    if changed:
        db.commit()
