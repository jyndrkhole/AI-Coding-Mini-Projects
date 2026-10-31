import asyncio
import json

from app.core.config import get_settings
from app.database.connection import SessionLocal, init_db, reset_engine
from app.mcp.client import open_session, result_text
from app.services.seed import seed_if_empty


def _prepare():
    get_settings.cache_clear()
    reset_engine()
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


async def _walk():
    async with open_session() as session:
        tools = {tool.name for tool in (await session.list_tools()).tools}
        assert {"db_lookup", "list_destinations", "compute_trip_cost"} <= tools

        goa = await session.call_tool(
            "compute_trip_cost",
            {
                "travel_cost_per_person": 2800,
                "room_price_per_night": 3000,
                "daily_spend_per_person": 1500,
                "people": 4,
                "nights": 3,
                "budget_per_person": 12000,
            },
        )
        assert goa.isError is False
        figures = json.loads(result_text(goa))
        assert figures["total_per_person"] == 11800
        assert figures["within_budget"] is True
        assert figures["money_left_per_person"] == 200

        bad = await session.call_tool(
            "compute_trip_cost",
            {
                "travel_cost_per_person": 2800,
                "room_price_per_night": 3000,
                "daily_spend_per_person": 1500,
                "people": 0,
                "nights": 3,
            },
        )
        assert bad.isError is True

        places = json.loads((await session.read_resource("trips://destinations")).contents[0].text)
        assert any(item["place_id"] == "HAMPI" for item in places)
        hampi = json.loads((await session.read_resource("trips://place/HAMPI")).contents[0].text)
        assert hampi["name"] == "Hampi"
        assert hampi["stay_name"] == "Boulder View Guesthouse"
        assert hampi["room_price_per_night"] == 1500

        prompts = {item.name for item in (await session.list_prompts()).prompts}
        assert "plan_trip" in prompts
        rendered = await session.get_prompt(
            "plan_trip",
            {"place": "Goa", "people": "4", "nights": "3", "budget_per_person": "12000"},
        )
        assert "Goa" in rendered.messages[0].content.text
        assert "12000" in rendered.messages[0].content.text


def test_mcp_client_walkthrough():
    _prepare()
    asyncio.run(_walk())
