"""Local Guide agent. A separate process TripWise asks over A2A.

Run it and leave it running:

    python -m app.a2a.guide
"""

from __future__ import annotations

import uvicorn
from a2a.helpers import get_message_text, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, Role
from starlette.applications import Starlette

from app.ai.llm import LLMNotConfigured, get_chat_model
from app.core.config import get_settings

HOST, PORT = "127.0.0.1", 9999

LOCAL_NOTES = {
    "goa": "Do: Fort Aguada at sunset, Fontainhas walk in Panaji, Dudhsagar falls. Eat: fish thali, bebinca (veg: mushroom xacuti).",
    "gokarna": "Do: Om Beach, the cliff trek from Kudle to Half Moon Beach, Mahabaleshwar temple. Eat: Udupi thali, neer dosa.",
    "pondicherry": "Do: White Town walk, Auroville, Paradise Beach. Eat: French bakery croissants, Creole curry.",
    "coorg": "Do: Abbey Falls, a coffee plantation tour, Raja's Seat at sunset. Eat: akki roti, bamboo shoot curry.",
    "ooty": "Do: toy train to Coonoor, Botanical Garden, Doddabetta Peak. Eat: homemade chocolates, varkey biscuits.",
    "manali": "Do: Solang Valley, Old Manali cafes, Hadimba Temple. Eat: siddu, rajma chawal.",
    "hampi": "Do: Virupaksha Temple, sunrise at Matanga Hill, coracle ride on the Tungabhadra. Eat: thali meals, banana pancakes.",
    "jaipur": "Do: Amber Fort, Hawa Mahal, Nahargarh at sunset. Eat: dal baati churma, pyaaz kachori.",
    "rishikesh": "Do: river rafting (Oct–Jun), Ganga aarti at Triveni Ghat, Laxman Jhula. Eat: Chotiwala thali, cafe pancakes.",
    "dandeli": "Do: white-water rafting on the Kali (Oct–May), Syntheri Rocks, jungle safari. Eat: Malnad meals, kokum juice.",
}

skill = AgentSkill(
    id="local_tips",
    name="Local tips",
    description="Things to do, local food to try and weather warnings for an Indian travel destination in a given month.",
    tags=["travel", "local guide"],
    examples=["What should we do in Hampi in December?"],
)

agent_card = AgentCard(
    name="Local Guide Agent",
    description="Knows what to do, what to eat and what weather to expect at popular Indian trips. It does not quote prices.",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[AgentInterface(protocol_binding="JSONRPC", url=f"http://{HOST}:{PORT}", protocol_version="1.0")],
    skills=[skill],
)


def notes_for(question: str) -> str:
    return next((note for place, note in LOCAL_NOTES.items() if place in question.lower()), "No notes for this place.")


async def guide_brain(question: str) -> str:
    notes = notes_for(question)
    try:
        reply = await get_chat_model().ainvoke([
            (
                "system",
                "You are a friendly local guide for Indian destinations. Using only the notes, give 3 things to do, "
                "1 local food to try, and 1 weather warning for the month asked. Under 80 words. "
                "Do not invent prices. If the notes say there is no entry for this place, say so.\n"
                f"Notes: {notes}",
            ),
            ("human", question),
        ])
        text = getattr(reply, "text", None) or getattr(reply, "content", "")
        return str(text)
    except LLMNotConfigured:
        return f"Stored local notes, not a live report: {notes}"


class GuideExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        question = get_message_text(context.message)
        answer = await guide_brain(question)
        await event_queue.enqueue_event(new_text_message(answer, role=Role.ROLE_AGENT))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported.")


def build_app() -> Starlette:
    handler = DefaultRequestHandler(agent_executor=GuideExecutor(), task_store=InMemoryTaskStore(), agent_card=agent_card)
    return Starlette(routes=create_agent_card_routes(agent_card) + create_jsonrpc_routes(handler, "/"))


app = build_app()


def main() -> None:
    settings = get_settings()
    print(f"Local Guide Agent running at http://{HOST}:{PORT}")
    print(f"Agent card: http://{HOST}:{PORT}/.well-known/agent-card.json")
    print(f"TripWise should use GUIDE_URL={settings.guide_url}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
