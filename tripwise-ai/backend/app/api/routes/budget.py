from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.pipeline import compare_destinations, run_budget_pipeline
from app.services.budget import calculate_budget_buffer, calculate_stay_share, calculate_travel_budget, calculate_trip_cost

router = APIRouter(prefix="/api/budget", tags=["budget"])


class PipelineIn(BaseModel):
    place: str = Field(min_length=2)
    people: int = Field(ge=1, le=20)
    nights: int = Field(ge=1, le=30)
    budget_per_person: float = Field(ge=0)


class CalculateIn(BaseModel):
    people: int = Field(ge=1, le=20)
    nights: int = Field(ge=1, le=30)
    room_price_per_night: float = Field(ge=0)
    travel_per_person: float = Field(ge=0)
    food_per_person_per_day: float = Field(ge=0, default=0)
    local_transport_per_person_per_day: float = Field(ge=0, default=0)
    activities_per_person: float = Field(ge=0, default=0)
    entry_tickets_per_person: float = Field(ge=0, default=0)
    shopping_per_person: float = Field(ge=0, default=0)
    miscellaneous_per_person: float = Field(ge=0, default=0)
    buffer_rate: float = Field(ge=0, le=1, default=0.10)
    budget_total: float | None = Field(default=None, ge=0)


class CompareIn(BaseModel):
    places: list[str] = Field(min_length=2, max_length=3)
    people: int = Field(ge=1, le=20)
    nights: int = Field(ge=1, le=30)
    budget_per_person: float | None = Field(default=None, ge=0)


class LessonIn(BaseModel):
    travel_cost_per_person: float = Field(ge=0)
    room_price_per_night: float = Field(ge=0)
    daily_spend_per_person: float = Field(ge=0)
    people: int = Field(ge=1, le=20)
    nights: int = Field(ge=1, le=30)


@router.post("/pipeline")
async def pipeline(body: PipelineIn):
    """MCP lookup, exact cost tool, then the two explanation chains."""
    result = await run_budget_pipeline(body.place, body.people, body.nights, body.budget_per_person)
    if result.get("error") and "tool_result" not in result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": result["error"]})
    return {"success": True, "data": result}


@router.post("/calculate")
def calculate(body: CalculateIn):
    try:
        data = calculate_travel_budget(
            people=body.people,
            nights=body.nights,
            room_price_per_night=body.room_price_per_night,
            travel_per_person=body.travel_per_person,
            food_per_person_per_day=body.food_per_person_per_day,
            local_transport_per_person_per_day=body.local_transport_per_person_per_day,
            activities_per_person=body.activities_per_person,
            entry_tickets_per_person=body.entry_tickets_per_person,
            shopping_per_person=body.shopping_per_person,
            miscellaneous_per_person=body.miscellaneous_per_person,
            buffer_rate=body.buffer_rate,
            budget_total=body.budget_total,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "invalid", "message": str(exc)}) from exc
    return {"success": True, "data": data}


@router.post("/lesson")
def lesson_formula(body: LessonIn):
    """The lesson 04/06 formula, with no model involved."""
    stay = calculate_stay_share(body.room_price_per_night, body.nights, body.people)
    cost = calculate_trip_cost(body.travel_cost_per_person, stay["stay_share"], body.daily_spend_per_person, body.nights)
    buffer = calculate_budget_buffer(cost["cost_per_person"])
    return {"success": True, "data": {**stay, **cost, "buffer": buffer}}


@router.post("/compare")
async def compare(body: CompareIn):
    data = await compare_destinations(body.places, body.people, body.nights, body.budget_per_person)
    return {"success": True, "data": data}
