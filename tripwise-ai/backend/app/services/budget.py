"""Exact trip arithmetic.

These formulas come from the lesson scripts. The model is not allowed to
replace them. Every figure is a demonstration estimate unless a future
integration supplies a live fare.
"""

import math
from decimal import Decimal

from app.utils.money import as_float, to_decimal

ROOM_CAPACITY = 2
DEFAULT_BUFFER_RATE = Decimal("0.10")

ASSUMPTIONS = [
    "One room fits 2 people. Rooms needed are people / 2, rounded up.",
    "Stay share is rooms x room price per night x nights / people.",
    "Cost per person is travel + stay share + daily spend x nights, unless a category breakdown is supplied.",
    "The default emergency buffer is 10 percent of the total before buffer.",
    "Room prices and travel amounts are demonstration estimates stored in SQLite, not live fares or availability.",
]


def rooms_needed(people: int) -> int:
    if people < 1:
        raise ValueError("people must be at least 1")
    return math.ceil(people / ROOM_CAPACITY)


def calculate_stay_share(room_price_per_night, nights: int, people: int) -> dict:
    if nights < 1:
        raise ValueError("nights must be at least 1")
    price = to_decimal(room_price_per_night)
    if price < 0:
        raise ValueError("room price cannot be negative")
    rooms = rooms_needed(people)
    share = to_decimal((Decimal(rooms) * price * Decimal(nights)) / Decimal(people))
    room_total = to_decimal(Decimal(rooms) * price * Decimal(nights))
    return {
        "rooms_needed": rooms,
        "room_capacity": ROOM_CAPACITY,
        "room_price_per_night": as_float(price),
        "nights": nights,
        "people": people,
        "room_total": as_float(room_total),
        "stay_share": as_float(share),
        "assumptions": ASSUMPTIONS[:2],
        "source": "python_calculation",
    }


def calculate_trip_cost(travel_cost_per_person, stay_share, daily_spend_per_person, nights: int) -> dict:
    if nights < 1:
        raise ValueError("nights must be at least 1")
    travel = to_decimal(travel_cost_per_person)
    stay = to_decimal(stay_share)
    daily = to_decimal(daily_spend_per_person)
    for label, amount in (("travel", travel), ("stay share", stay), ("daily spend", daily)):
        if amount < 0:
            raise ValueError(f"{label} cannot be negative")
    food_and_fun = to_decimal(daily * Decimal(nights))
    total = to_decimal(travel + stay + food_and_fun)
    return {
        "travel_cost_per_person": as_float(travel),
        "stay_share": as_float(stay),
        "daily_spend_per_person": as_float(daily),
        "nights": nights,
        "food_and_fun": as_float(food_and_fun),
        "cost_per_person": as_float(total),
        "assumptions": [ASSUMPTIONS[2], ASSUMPTIONS[4]],
        "source": "python_calculation",
    }


def calculate_travel_budget(
    people: int,
    nights: int,
    room_price_per_night,
    travel_per_person,
    food_per_person_per_day=0,
    local_transport_per_person_per_day=0,
    activities_per_person=0,
    entry_tickets_per_person=0,
    shopping_per_person=0,
    miscellaneous_per_person=0,
    buffer_rate=DEFAULT_BUFFER_RATE,
    budget_total=None,
) -> dict:
    """Category budget. Daily food and local transport are multiplied by nights.

    Activities, tickets, shopping, and miscellaneous are trip totals per person.
    Accommodation still uses the shared-room rule.
    """
    stay = calculate_stay_share(room_price_per_night, nights, people)
    food_day = to_decimal(food_per_person_per_day)
    local_day = to_decimal(local_transport_per_person_per_day)
    travel = to_decimal(travel_per_person)
    activities = to_decimal(activities_per_person)
    tickets = to_decimal(entry_tickets_per_person)
    shopping = to_decimal(shopping_per_person)
    miscellaneous = to_decimal(miscellaneous_per_person)
    rate = to_decimal(buffer_rate)
    if rate < 0 or rate > 1:
        raise ValueError("buffer rate must be between 0 and 1")

    per_person_categories = {
        "travel": travel,
        "accommodation_share": to_decimal(stay["stay_share"]),
        "food": to_decimal(food_day * Decimal(nights)),
        "local_transport": to_decimal(local_day * Decimal(nights)),
        "activities": activities,
        "entry_tickets": tickets,
        "shopping": shopping,
        "miscellaneous": miscellaneous,
    }
    subtotal_per_person = to_decimal(sum(per_person_categories.values(), Decimal("0")))
    buffer_per_person = to_decimal(subtotal_per_person * rate)
    per_person = to_decimal(subtotal_per_person + buffer_per_person)
    total = to_decimal(per_person * Decimal(people))
    per_day = to_decimal(per_person / Decimal(nights))

    result = {
        "people": people,
        "nights": nights,
        "rooms_needed": stay["rooms_needed"],
        "categories_per_person": {key: as_float(value) for key, value in per_person_categories.items()},
        "subtotal_per_person": as_float(subtotal_per_person),
        "buffer_rate": as_float(rate),
        "buffer_per_person": as_float(buffer_per_person),
        "cost_per_person": as_float(per_person),
        "cost_per_day": as_float(per_day),
        "total_trip_cost": as_float(total),
        "assumptions": ASSUMPTIONS,
        "source": "python_calculation",
        "price_label": "demonstration_estimate",
    }
    if budget_total is not None:
        budget = to_decimal(budget_total)
        remaining = to_decimal(budget - total)
        result["budget_total"] = as_float(budget)
        result["remaining_budget"] = as_float(remaining)
        result["budget_utilization"] = as_float(to_decimal((total / budget) * Decimal("100"))) if budget > 0 else None
        result["within_budget"] = remaining >= 0
    return result


def calculate_budget_buffer(total, rate=DEFAULT_BUFFER_RATE) -> dict:
    amount = to_decimal(total)
    buffer_rate = to_decimal(rate)
    if amount < 0:
        raise ValueError("total cannot be negative")
    if buffer_rate < 0 or buffer_rate > 1:
        raise ValueError("buffer rate must be between 0 and 1")
    buffer = to_decimal(amount * buffer_rate)
    return {
        "base_total": as_float(amount),
        "buffer_rate": as_float(buffer_rate),
        "buffer_amount": as_float(buffer),
        "total_with_buffer": as_float(to_decimal(amount + buffer)),
        "assumptions": [ASSUMPTIONS[3]],
        "source": "python_calculation",
    }


def compare_trip_budgets(plans: list[dict]) -> dict:
    """Compare already-calculated per-person totals. Does not invent missing plans."""
    if len(plans) < 2:
        raise ValueError("at least two plans are required")
    ranked = sorted(plans, key=lambda item: to_decimal(item["cost_per_person"]))
    lowest = ranked[0]
    highest = ranked[-1]
    return {
        "plans": plans,
        "lowest": lowest,
        "highest": highest,
        "difference_per_person": as_float(
            to_decimal(to_decimal(highest["cost_per_person"]) - to_decimal(lowest["cost_per_person"]))
        ),
        "source": "python_calculation",
    }
