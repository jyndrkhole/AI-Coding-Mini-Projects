"""Day-wise itineraries built from attraction rows. The model can explain them, not invent the stops."""

import json

from app.database.models import Attraction, Destination, TravelTip
from app.database.repositories.destinations import DestinationRepository


def _block(title: str, detail: str, duration: str, cost: float, when: str, source: str) -> dict:
    return {
        "title": title,
        "detail": detail,
        "duration": duration,
        "estimated_cost": cost,
        "time_of_day": when,
        "source": source,
        "price_label": "demonstration_estimate",
    }


def _food(tips: list[TravelTip]) -> dict:
    for tip in tips:
        if tip.category == "food":
            return {"suggestion": tip.content, "source": "travel_tip", "title": tip.title}
    return {
        "suggestion": "Eat at a busy local place near the stay. This is a general suggestion, not a verified restaurant booking.",
        "source": "general_suggestion",
        "title": "Food",
    }


def _tip_text(tips: list[TravelTip]) -> str:
    preferred = [tip for tip in tips if tip.category in {"practical", "safety", "season"}]
    chosen = preferred[0] if preferred else (tips[0] if tips else None)
    if not chosen:
        return "No destination-specific tip is stored. Treat timing and access as unverified."
    return f"{chosen.title}: {chosen.content}"


def _from_attraction(item: Attraction, when: str) -> dict:
    return _block(
        item.name,
        item.description,
        item.ideal_duration,
        float(item.estimated_cost or 0),
        when,
        "attraction",
    )


def build_itinerary(repo: DestinationRepository, destination: Destination, days: int) -> list[dict]:
    if days < 1 or days > 14:
        raise ValueError("days must be between 1 and 14")
    attractions = repo.attractions(destination.id)
    tips = [tip for tip in repo.tips(destination.id) if tip.destination_id == destination.id]
    food = _food(tips)
    practical = _tip_text(tips)
    if not attractions:
        raise ValueError(f"No attractions are stored for {destination.name}, so an itinerary cannot be built.")

    plan: list[dict] = []
    cursor = 0

    def take(when: str) -> dict:
        nonlocal cursor
        item = attractions[cursor % len(attractions)]
        cursor += 1
        return _from_attraction(item, when)

    for day_number in range(1, days + 1):
        if days == 1:
            title = "A single day on the ground"
            morning, afternoon, evening = take("morning"), take("afternoon"), take("evening")
        elif day_number == 1:
            title = "Arrival and local exploration"
            morning = _block(
                f"Arrive in {destination.name}",
                f"Settle in and keep the first block light. Ideal trip length on record is {destination.ideal_duration_days} days.",
                "travel",
                0,
                "morning",
                "itinerary_rule",
            )
            afternoon = take("afternoon")
            evening = _block(
                "Neighbourhood walk",
                "Stay close to the accommodation. Do not treat opening hours as confirmed.",
                "1 hour",
                0,
                "evening",
                "itinerary_rule",
            )
        elif day_number == days:
            title = "Departure"
            morning = take("morning")
            afternoon = _block(
                "Leave for the station or airport",
                "Keep a buffer before departure. Ticket prices are not live.",
                "travel",
                0,
                "afternoon",
                "itinerary_rule",
            )
            evening = _block("Travel home", "No further sightseeing is scheduled.", "travel", 0, "evening", "itinerary_rule")
        else:
            title = "Main sights" if day_number == 2 else "Experiences and a slower block"
            morning, afternoon, evening = take("morning"), take("afternoon"), take("evening")

        activities = {
            "morning": morning,
            "afternoon": afternoon,
            "evening": evening,
            "sequence": ["morning", "afternoon", "evening"],
            "food": food,
            "tip": practical,
        }
        cost = sum(
            float(activities[slot].get("estimated_cost") or 0)
            for slot in ("morning", "afternoon", "evening")
        )
        plan.append(
            {
                "day_number": day_number,
                "title": f"Day {day_number} — {title}",
                "activities": activities,
                "estimated_cost": round(cost, 2),
            }
        )
    return plan


def regenerate_day(repo: DestinationRepository, destination: Destination, day: dict) -> dict:
    """Replace one day with the next stored attractions, leaving the other days untouched."""
    attractions = repo.attractions(destination.id)
    if not attractions:
        raise ValueError("No attractions are stored for this destination.")
    activities = day["activities"]
    used = {
        activities.get(slot, {}).get("title")
        for slot in ("morning", "afternoon", "evening")
    }
    fresh = [item for item in attractions if item.name not in used] or attractions
    slots = ["morning", "afternoon", "evening"]
    for index, slot in enumerate(slots):
        current = activities.get(slot) or {}
        if current.get("source") == "itinerary_rule" and slot != "morning":
            continue
        item = fresh[index % len(fresh)]
        activities[slot] = _from_attraction(item, slot)
    cost = sum(float(activities[slot].get("estimated_cost") or 0) for slot in slots)
    day["activities"] = activities
    day["estimated_cost"] = round(cost, 2)
    day["title"] = day["title"].split("—")[0].strip() + " — Regenerated from stored attractions"
    return day


def dumps_activities(day: dict) -> str:
    return json.dumps(day["activities"])
