"""Lesson 07 pipeline, with the tool call sent to the MCP server instead of an in-process function."""

from __future__ import annotations

import logging

from app.ai.chains import decide_budget, explain_cost
from app.ai.llm import LLMNotConfigured
from app.core.config import get_settings
from app.mcp.client import open_session, parse_tool_payload

logger = logging.getLogger(__name__)


async def lookup_and_cost(place: str, people: int, nights: int, budget_per_person: float | None = None) -> dict:
    async with open_session() as session:
        return await lookup_and_cost_in_session(session, place, people, nights, budget_per_person)


async def lookup_and_cost_in_session(session, place, people, nights, budget_per_person):
    lookup = await session.call_tool("db_lookup", {"place": place})
    record = parse_tool_payload(lookup)
    if lookup.isError or not isinstance(record, dict) or record.get("error"):
        message = record.get("error") if isinstance(record, dict) else "Destination lookup failed."
        return {"error": message or "Destination lookup failed."}
    arguments = {
        "travel_cost_per_person": record["travel_cost_per_person"],
        "room_price_per_night": record["room_price_per_night"],
        "daily_spend_per_person": record["daily_spend_per_person"],
        "people": people,
        "nights": nights,
    }
    if budget_per_person is not None:
        arguments["budget_per_person"] = budget_per_person
    cost_call = await session.call_tool("compute_trip_cost", arguments)
    tool_result = parse_tool_payload(cost_call)
    if cost_call.isError or not isinstance(tool_result, dict) or tool_result.get("error"):
        return {"error": "The cost tool rejected these inputs.", "record": record, "tool_result": tool_result}
    return {"record": record, "tool_result": tool_result}


async def run_budget_pipeline(place: str, people: int, nights: int, budget_per_person: float) -> dict:
    """DB via MCP, exact tool, chain 1 explains, chain 2 decides."""
    found = await lookup_and_cost(place, people, nights, budget_per_person)
    if found.get("error") and "tool_result" not in found:
        return found
    record = found["record"]
    tool_result = found["tool_result"]
    rule = "GO" if tool_result.get("within_budget") else "NOT YET"
    breakdown = None
    decision = None
    chain_error = ""
    if get_settings().llm_configured:
        try:
            breakdown = explain_cost({**record, **tool_result, "people": people, "nights": nights})
            decision = decide_budget(record["name"], budget_per_person, breakdown)
        except LLMNotConfigured:
            chain_error = "The language model is not configured."
        except Exception:
            logger.exception("budget chains failed")
            chain_error = "The explanation chains failed. The tool figures are still valid."
    return {
        "record": record,
        "tool_result": tool_result,
        "breakdown": breakdown,
        "decision": decision,
        "rule_decision": rule,
        "chain_error": chain_error,
        "price_label": "demonstration_estimate",
    }


async def compare_destinations(places: list[str], people: int, nights: int, budget_per_person: float | None) -> dict:
    rows = []
    missing = []
    async with open_session() as session:
        for place in places:
            found = await lookup_and_cost_in_session(session, place, people, nights, budget_per_person)
            if found.get("error") and "record" not in found:
                missing.append({"place": place, "error": found["error"]})
                continue
            record = found["record"]
            tool_result = found.get("tool_result") or {}
            rows.append({**record, **tool_result})
    rows.sort(key=lambda item: item.get("total_per_person", 0))
    return {"rows": rows, "missing": missing, "price_label": "demonstration_estimate"}
