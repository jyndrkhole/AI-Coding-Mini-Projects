"""TripWise MCP server.

Same three building blocks as the Trip Buddy lessons:
tools the model may call, resources the app reads, and a prompt the user picks.

stdout is the protocol. This file must not print.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)

from app.database.connection import SessionLocal, init_db
from app.database.repositories.destinations import DestinationRepository
from app.services.budget import calculate_stay_share, calculate_trip_cost

mcp = FastMCP("TripWise Server", log_level="WARNING")


def _session():
    init_db()
    return SessionLocal()


def fetch_place(place: str) -> dict | None:
    """JOIN destination, default stay, and demonstration travel cost."""
    db = _session()
    try:
        repo = DestinationRepository(db)
        destination = repo.by_code(place) or repo.by_name(place) or repo.by_slug(place.lower())
        if destination is None:
            return None
        stay = repo.representative_stay(destination.id)
        if stay is None:
            return None
        return {
            "place_id": destination.code,
            "name": destination.name,
            "trip_type": destination.destination_type,
            "state": destination.state,
            "best_months": destination.best_season,
            "stay_name": stay.name,
            "room_price_per_night": float(stay.price_per_night),
            "travel_mode": destination.travel_mode,
            "travel_cost_per_person": float(destination.demo_travel_cost_per_person),
            "daily_spend_per_person": float(destination.demo_daily_spend_per_person),
            "price_label": "demonstration_estimate",
        }
    finally:
        db.close()


def list_places() -> list[dict]:
    db = _session()
    try:
        repo = DestinationRepository(db)
        rows = sorted(repo.list(), key=lambda item: (item.destination_type, item.name))
        return [
            {
                "place_id": item.code,
                "name": item.name,
                "trip_type": item.destination_type,
                "best_months": item.best_season,
            }
            for item in rows
        ]
    finally:
        db.close()


@mcp.tool()
def db_lookup(
    place: Annotated[str, Field(description="Place name like 'Goa' or id like 'PONDY'")],
) -> dict:
    """Fetch a destination's trip type, best months, stay, room price, travel cost and daily spend from the database."""
    record = fetch_place(place)
    return record if record else {"error": f"{place} not found. Use list_destinations to see valid places."}


@mcp.tool()
def list_destinations() -> list[dict]:
    """Return all destinations in the database."""
    return list_places()


@mcp.tool()
def compute_trip_cost(
    travel_cost_per_person: Annotated[float, Field(ge=0, description="Return travel cost for one person, in rupees")],
    room_price_per_night: Annotated[float, Field(ge=0, description="Price of one room for one night (a room fits 2)")],
    daily_spend_per_person: Annotated[float, Field(ge=0, description="Food, local travel and fun per person per day")],
    people: Annotated[int, Field(ge=1, le=20, description="Number of travellers (1-20)")],
    nights: Annotated[int, Field(ge=1, le=30, description="Number of nights (1-30)")],
    budget_per_person: Annotated[float | None, Field(description="Optional budget per person, in rupees")] = None,
) -> dict:
    """Compute the trip cost per person with exact arithmetic.

    One room fits 2 people. Returns rooms_needed, stay_share_per_person,
    food_and_fun_per_person, total_per_person, and, if a budget is given,
    within_budget and money_left_per_person (negative means over budget).
    """
    stay = calculate_stay_share(room_price_per_night, nights, people)
    cost = calculate_trip_cost(travel_cost_per_person, stay["stay_share"], daily_spend_per_person, nights)
    result = {
        "rooms_needed": stay["rooms_needed"],
        "stay_share_per_person": cost["stay_share"],
        "food_and_fun_per_person": cost["food_and_fun"],
        "total_per_person": cost["cost_per_person"],
        "price_label": "demonstration_estimate",
        "source": "python_calculation",
    }
    if budget_per_person is not None:
        result["within_budget"] = cost["cost_per_person"] <= budget_per_person
        result["money_left_per_person"] = round(budget_per_person - cost["cost_per_person"], 2)
    return result


@mcp.resource("trips://destinations", mime_type="application/json")
def destinations_resource() -> str:
    """All destinations with their trip type and best months."""
    return json.dumps(list_places(), ensure_ascii=False)


@mcp.resource("trips://place/{place_id}", mime_type="application/json")
def place_resource(place_id: str) -> str:
    """One destination's full record, for example trips://place/HAMPI."""
    return json.dumps(fetch_place(place_id) or {"error": f"{place_id} not found"}, ensure_ascii=False)


@mcp.prompt()
def plan_trip(place: str, people: str, nights: str, budget_per_person: str) -> str:
    """Plan a trip: fills the group's details into a well-phrased question."""
    return (
        f"We are {people} friends with ₹{budget_per_person} each. "
        f"Can we do {place} for {nights} nights? "
        "Give the cost per person, say whether it fits our budget, and add 2 useful tips."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
