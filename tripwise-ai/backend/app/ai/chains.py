"""Lesson 07 chains: explain the tool numbers, then decide GO or NOT YET.

The second chain reads the first chain's text. Neither chain is allowed to recompute.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm import get_chat_model

EXPLAIN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are TripWise AI, a practical travel advisor.\n"
        "The numbers below were calculated by a trusted tool. Do NOT redo them.\n"
        "They are demonstration estimates, not live fares or availability.\n"
        "Explain the cost breakdown in plain language and end with:\n"
        "COST_PER_PERSON: {total_per_person}",
    ),
    (
        "human",
        "Trip: {name} ({trip_type}), best months {best_months}\n"
        "Group: {people} travellers, {nights} nights at {stay_name}\n"
        "Travel: {travel_mode}, ₹{travel_cost_per_person} per person\n\n"
        "Tool results:\n"
        "  Rooms needed     : {rooms_needed}\n"
        "  Stay share       : ₹{stay_share_per_person}\n"
        "  Food and fun     : ₹{food_and_fun_per_person}\n"
        "  Total per person : ₹{total_per_person}",
    ),
])

DECIDE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are TripWise AI.\n"
        "Money left per person = budget - total cost per person. Use the breakdown, do not recompute.\n"
        "Say clearly: GO (within budget) or NOT YET (over budget).\n"
        "If over budget, suggest one simple change using only the numbers already given.\n"
        "Remind the traveller these are demonstration estimates.",
    ),
    (
        "human",
        "Trip: {name} | Budget per person: ₹{budget_per_person}\n\n"
        "Cost breakdown:\n{breakdown}",
    ),
])


def explain_cost(payload: dict) -> str:
    chain = EXPLAIN_PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke(payload)


def decide_budget(name: str, budget_per_person: float, breakdown: str) -> str:
    chain = DECIDE_PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke(
        {"name": name, "budget_per_person": budget_per_person, "breakdown": breakdown}
    )
