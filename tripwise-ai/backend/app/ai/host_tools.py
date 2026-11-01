"""Catalogue and notebook tools that run in the API process.

Price arithmetic still uses the budget module. The MCP server remains the
lesson path for db_lookup, list_destinations, and compute_trip_cost.
"""

from __future__ import annotations

import json

from app.ai.retriever import retrieve_context
from app.database.connection import SessionLocal, init_db
from app.database.repositories.destinations import DestinationRepository, serialize_detail
from app.services.budget import calculate_budget_buffer, calculate_stay_share, calculate_trip_cost, compare_trip_budgets
from app.services.itinerary import build_itinerary
from app.utils.money import as_float, to_decimal

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _db():
    init_db()
    return SessionLocal()


def _destination(repo: DestinationRepository, place: str):
    return repo.by_code(place) or repo.by_name(place) or repo.by_slug(place.lower())


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}
_NUM = {"type": "number"}

HOST_SCHEMAS = [
    _schema(
        "search_destinations",
        "Search the destination catalogue by text, type, or audience. Does not return live prices.",
        {"query": _STR, "destination_type": _STR, "audience": _STR},
        [],
    ),
    _schema(
        "get_destination_details",
        "Full catalogue record for one place: description, stays, attractions, tips, and nearby places.",
        {"place": _STR},
        ["place"],
    ),
    _schema(
        "get_nearby_destinations",
        "Nearby places stored for this destination. Do not guess places that are not returned.",
        {"place": _STR},
        ["place"],
    ),
    _schema(
        "lookup_accommodation",
        "Stored sample stays and demonstration room prices for one place.",
        {"place": _STR},
        ["place"],
    ),
    _schema(
        "search_attractions",
        "Stored attractions, sample costs, and duration for one place.",
        {"place": _STR},
        ["place"],
    ),
    _schema(
        "get_destination_prices",
        "Demonstration travel, room, and daily-spend figures plus family, couple, and adventure labels.",
        {"place": _STR},
        ["place"],
    ),
    _schema(
        "retrieve_travel_knowledge",
        "Semantic notebook search. Optional filters: destination name, travel type, season month.",
        {"query": _STR, "destination": _STR, "travel_type": _STR, "season": _STR},
        ["query"],
    ),
    _schema(
        "search_seasonal_tips",
        "Notebook notes for a season or month. Say when nothing is stored.",
        {"query": _STR, "season": _STR},
        ["query"],
    ),
    _schema(
        "search_travel_safety_information",
        "Notebook safety notes. Do not invent weather or restrictions.",
        {"query": _STR},
        ["query"],
    ),
    _schema(
        "generate_daywise_itinerary",
        "Build a day plan from stored attractions only.",
        {"place": _STR, "days": _INT},
        ["place", "days"],
    ),
    _schema(
        "estimate_activity_cost",
        "Sum stored attraction sample costs for one place. Python does the addition.",
        {"place": _STR},
        ["place"],
    ),
    _schema(
        "optimize_destination_sequence",
        "Order named places by the catalogue's ideal duration. This is not a road-route engine.",
        {"places": {"type": "array", "items": _STR}},
        ["places"],
    ),
    _schema(
        "calculate_stay_share",
        "Exact stay share. Pass the room price returned by a lookup tool. One room fits 2 people.",
        {"room_price_per_night": _NUM, "nights": _INT, "people": _INT},
        ["room_price_per_night", "nights", "people"],
    ),
    _schema(
        "calculate_budget_buffer",
        "Exact buffer on a total that a cost tool already returned. Default rate is 0.10.",
        {"total": _NUM, "rate": _NUM},
        ["total"],
    ),
    _schema(
        "compare_destination_costs",
        "Compare demonstration cost per person for 2 or 3 places. Python does the arithmetic.",
        {"places": {"type": "array", "items": _STR}, "people": _INT, "nights": _INT},
        ["places", "people", "nights"],
    ),
]

HOST_NAMES = {item["function"]["name"] for item in HOST_SCHEMAS}


def detect_notebook_filters(query: str, place_names: list[str]) -> dict:
    lower = query.lower()
    found = {}
    for name in sorted(place_names, key=len, reverse=True):
        if name and name.lower() in lower:
            found["destination"] = name
            break
    for month in MONTH_NAMES:
        if month.lower() in lower:
            found["season"] = month
            break
    return found


def run_host_tool(name: str, args: dict) -> dict:
    try:
        handler = _HANDLERS[name]
    except KeyError:
        return {"error": f"Unknown catalogue tool {name}"}
    try:
        return handler(args or {})
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception:
        return {"error": f"{name} could not be completed."}


def _search(args: dict) -> dict:
    db = _db()
    try:
        rows = DestinationRepository(db).list(
            q=args.get("query") or None,
            destination_type=args.get("destination_type") or None,
            audience=args.get("audience") or None,
        )
        return {
            "count": len(rows),
            "destinations": [
                {
                    "name": row.name,
                    "code": row.code,
                    "state": row.state,
                    "destination_type": row.destination_type,
                    "best_season": row.best_season,
                    "ideal_duration_days": row.ideal_duration_days,
                    "family_fit": row.family_fit,
                    "couple_fit": row.couple_fit,
                    "adventure_fit": row.adventure_fit,
                }
                for row in rows
            ],
        }
    finally:
        db.close()


def _details(args: dict) -> dict:
    db = _db()
    try:
        repo = DestinationRepository(db)
        destination = _destination(repo, str(args.get("place") or ""))
        if destination is None:
            return {"error": "That place is not in the catalogue."}
        loaded = repo.get(destination.id)
        return serialize_detail(repo, loaded)
    finally:
        db.close()


def _nearby(args: dict) -> dict:
    detail = _details(args)
    if detail.get("error"):
        return detail
    return {"place": detail["name"], "nearby": detail.get("nearby") or []}


def _stays(args: dict) -> dict:
    detail = _details(args)
    if detail.get("error"):
        return detail
    return {
        "place": detail["name"],
        "accommodations": detail.get("accommodations") or [],
        "price_label": "demonstration_estimate",
    }


def _attractions(args: dict) -> dict:
    detail = _details(args)
    if detail.get("error"):
        return detail
    return {"place": detail["name"], "attractions": detail.get("attractions") or []}


def _prices(args: dict) -> dict:
    db = _db()
    try:
        repo = DestinationRepository(db)
        destination = _destination(repo, str(args.get("place") or ""))
        if destination is None:
            return {"error": "That place is not in the catalogue."}
        stay = repo.representative_stay(destination.id)
        if stay is None:
            return {"error": "No sample stay is stored for that place."}
        return {
            "place_id": destination.code,
            "name": destination.name,
            "room_price_per_night": float(stay.price_per_night),
            "stay_name": stay.name,
            "travel_cost_per_person": float(destination.demo_travel_cost_per_person),
            "daily_spend_per_person": float(destination.demo_daily_spend_per_person),
            "travel_mode": destination.travel_mode,
            "family_fit": destination.family_fit,
            "couple_fit": destination.couple_fit,
            "adventure_fit": destination.adventure_fit,
            "price_label": "demonstration_estimate",
        }
    finally:
        db.close()


def _knowledge(args: dict) -> dict:
    text = retrieve_context(
        str(args.get("query") or ""),
        destination=args.get("destination") or None,
        travel_type=args.get("travel_type") or None,
        season=args.get("season") or None,
    )
    return {"notes": text, "source": "notebook"}


def _seasonal(args: dict) -> dict:
    season = args.get("season") or ""
    query = str(args.get("query") or "seasonal travel")
    return _knowledge({"query": f"{query} {season}".strip(), "season": season})


def _safety(args: dict) -> dict:
    return _knowledge({"query": f"safety {args.get('query') or ''}".strip()})


def _itinerary(args: dict) -> dict:
    days = int(args.get("days") or 0)
    db = _db()
    try:
        repo = DestinationRepository(db)
        destination = _destination(repo, str(args.get("place") or ""))
        if destination is None:
            return {"error": "That place is not in the catalogue."}
        plan = build_itinerary(repo, destination, days)
        return {"place": destination.name, "days": plan, "price_label": "demonstration_estimate"}
    finally:
        db.close()


def _activity_cost(args: dict) -> dict:
    db = _db()
    try:
        repo = DestinationRepository(db)
        destination = _destination(repo, str(args.get("place") or ""))
        if destination is None:
            return {"error": "That place is not in the catalogue."}
        attractions = repo.attractions(destination.id)
        total = to_decimal(0)
        items = []
        for item in attractions:
            cost = to_decimal(item.estimated_cost or 0)
            total = to_decimal(total + cost)
            items.append({"name": item.name, "estimated_cost": as_float(cost)})
        return {
            "place": destination.name,
            "attractions": items,
            "sample_activity_total": as_float(total),
            "price_label": "demonstration_estimate",
            "source": "python_calculation",
        }
    finally:
        db.close()


def _sequence(args: dict) -> dict:
    names = [str(item).strip() for item in (args.get("places") or []) if str(item).strip()]
    if len(names) < 2:
        return {"error": "Name at least two places."}
    db = _db()
    try:
        repo = DestinationRepository(db)
        ordered = []
        missing = []
        for name in names:
            destination = _destination(repo, name)
            if destination is None:
                missing.append(name)
            else:
                ordered.append(destination)
        ordered.sort(key=lambda item: (item.ideal_duration_days, item.name))
        return {
            "sequence": [
                {"name": item.name, "ideal_duration_days": item.ideal_duration_days, "travel_mode": item.travel_mode}
                for item in ordered
            ],
            "missing": missing,
            "note": "Ordered by the stored ideal duration. This is not a driving route.",
        }
    finally:
        db.close()


def _stay_share(args: dict) -> dict:
    result = calculate_stay_share(args["room_price_per_night"], int(args["nights"]), int(args["people"]))
    result["price_label"] = "demonstration_estimate"
    return result


def _buffer(args: dict) -> dict:
    rate = args.get("rate", 0.10)
    return calculate_budget_buffer(args["total"], rate)


def _compare(args: dict) -> dict:
    places = [str(item).strip() for item in (args.get("places") or []) if str(item).strip()]
    people = int(args.get("people") or 0)
    nights = int(args.get("nights") or 0)
    if not 2 <= len(places) <= 3:
        return {"error": "Compare two or three places."}
    db = _db()
    try:
        repo = DestinationRepository(db)
        plans = []
        missing = []
        for name in places:
            destination = _destination(repo, name)
            stay = repo.representative_stay(destination.id) if destination else None
            if destination is None or stay is None:
                missing.append(name)
                continue
            share = calculate_stay_share(stay.price_per_night, nights, people)
            cost = calculate_trip_cost(
                destination.demo_travel_cost_per_person,
                share["stay_share"],
                destination.demo_daily_spend_per_person,
                nights,
            )
            plans.append({"name": destination.name, "cost_per_person": cost["cost_per_person"], "price_label": "demonstration_estimate"})
        if len(plans) < 2:
            return {"error": "Not enough catalogue prices to compare.", "missing": missing}
        return {**compare_trip_budgets(plans), "missing": missing, "price_label": "demonstration_estimate"}
    finally:
        db.close()


_HANDLERS = {
    "search_destinations": _search,
    "get_destination_details": _details,
    "get_nearby_destinations": _nearby,
    "lookup_accommodation": _stays,
    "search_attractions": _attractions,
    "get_destination_prices": _prices,
    "retrieve_travel_knowledge": _knowledge,
    "search_seasonal_tips": _seasonal,
    "search_travel_safety_information": _safety,
    "generate_daywise_itinerary": _itinerary,
    "estimate_activity_cost": _activity_cost,
    "optimize_destination_sequence": _sequence,
    "calculate_stay_share": _stay_share,
    "calculate_budget_buffer": _buffer,
    "compare_destination_costs": _compare,
}


def tool_result_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)
