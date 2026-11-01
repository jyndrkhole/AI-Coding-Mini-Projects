"""Long-term memory for one traveller.

Short-term memory is the current chat. This module is the filing cabinet:
semantic facts, episodic past trips, and procedural planning rules.
The travel notebook stays separate. Memory is about the traveller, not the world.
"""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import get_embeddings
from app.ai.vector_store import get_client
from app.database.models import TravelerFact, TravelerRule

SHORT_TERM_LIMIT = 10
EPISODE_COLLECTION = "trip_episodes"
SECRET_PATTERN = re.compile(
    r"(\bpassword\b|\bpasscode\b|\bcvv\b|\bcard number\b|\baadhaar\b|\bpassport\b|\bphone\b|\b\d{10}\b|\b\d{13,19}\b)",
    re.IGNORECASE,
)

EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are the memory manager for TripWise, a trip planner.\n"
     "Read the chat and pick out ONLY what will help plan FUTURE trips for this traveller:\n"
     "- semantic: lasting facts (group size, home city, usual budget, food needs, health, likes, dislikes)\n"
     "- episodic: a past trip or event, with when, where and how it went, in one sentence\n"
     "- procedural: an instruction about how TripWise should plan for them from now on\n"
     "Skip small talk, one-off questions and TripWise's own answers.\n"
     "Never save passwords, card numbers, phone numbers or ID numbers.\n"
     "Reuse the same key when a fact already exists (so it can be updated).\n"
     "Return an empty list if nothing is worth remembering."),
    ("human", "Already in long-term memory:\n{existing}\n\nChat to read:\n{transcript}"),
])


class MemoryItem(BaseModel):
    type: Literal["semantic", "episodic", "procedural"] = Field(
        description="semantic = a lasting fact; episodic = a past trip; procedural = how to plan next time"
    )
    key: str = Field(default="", description="Semantic topic such as group_size. Empty otherwise.")
    content: str = Field(description="The memory itself, one short sentence.")


class MemoryList(BaseModel):
    memories: list[MemoryItem] = Field(default_factory=list)


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return str(content)


def trim(messages: list[dict], keep_last: int = SHORT_TERM_LIMIT) -> list[dict]:
    return messages[-keep_last:]


def looks_sensitive(text: str) -> bool:
    return bool(SECRET_PATTERN.search(text or ""))


def _episodes():
    return get_client().get_or_create_collection(EPISODE_COLLECTION, metadata={"hnsw:space": "cosine"})


def _today() -> str:
    return str(date.today())


class UserMemory:
    def __init__(self, db: Session, user_id: int, embed=None):
        self.db = db
        self.user_id = user_id
        self.embed = embed

    def _embed(self):
        return self.embed or get_embeddings()

    def set_fact(self, key: str, value: str) -> dict:
        key = key.strip().lower().replace(" ", "_") or "note"
        if looks_sensitive(key) or looks_sensitive(value):
            return {"action": "SKIP", "type": "semantic", "text": "sensitive detail was not saved"}
        row = self.db.scalars(
            select(TravelerFact).where(TravelerFact.user_id == self.user_id, TravelerFact.key == key)
        ).first()
        if row and row.value.strip().lower() == value.strip().lower():
            return {"action": "SKIP", "type": "semantic", "text": f"{key}: {value}"}
        old = row.value if row else None
        if row is None:
            row = TravelerFact(user_id=self.user_id, key=key, value=value.strip(), updated=_today())
            self.db.add(row)
        else:
            row.value = value.strip()
            row.updated = _today()
        self.db.commit()
        if old:
            return {"action": "UPDATE", "type": "semantic", "text": f"{key}: {value}", "old": old}
        return {"action": "ADD", "type": "semantic", "text": f"{key}: {value}"}

    def all_facts(self) -> dict:
        rows = self.db.scalars(
            select(TravelerFact).where(TravelerFact.user_id == self.user_id).order_by(TravelerFact.key)
        )
        return {row.key: row.value for row in rows}

    def add_episode(self, text: str) -> dict:
        cleaned = text.strip()
        if not cleaned or looks_sensitive(cleaned):
            return {"action": "SKIP", "type": "episodic", "text": "sensitive or empty detail was not saved"}
        collection = _episodes()
        vector = self._embed().embed_query(cleaned)
        existing = collection.get(where={"user_id": str(self.user_id)})
        if existing.get("ids"):
            near = collection.query(
                query_embeddings=[vector],
                n_results=1,
                where={"user_id": str(self.user_id)},
            )
            distances = (near.get("distances") or [[]])[0]
            if distances and distances[0] < 0.08:
                return {"action": "SKIP", "type": "episodic", "text": cleaned}
        collection.add(
            ids=[f"ep-{self.user_id}-{uuid.uuid4().hex[:12]}"],
            embeddings=[vector],
            documents=[cleaned],
            metadatas=[{"user_id": str(self.user_id), "saved": _today()}],
        )
        return {"action": "ADD", "type": "episodic", "text": cleaned}

    def search_episodes(self, query: str, n: int = 2) -> list[str]:
        collection = _episodes()
        existing = collection.get(where={"user_id": str(self.user_id)})
        count = len(existing.get("ids") or [])
        if count == 0:
            return []
        result = collection.query(
            query_embeddings=[self._embed().embed_query(query)],
            n_results=min(n, count),
            where={"user_id": str(self.user_id)},
        )
        return (result.get("documents") or [[]])[0]

    def all_episodes(self) -> list[str]:
        existing = _episodes().get(where={"user_id": str(self.user_id)})
        return list(existing.get("documents") or [])

    def add_rule(self, rule: str) -> dict:
        cleaned = rule.strip()
        if not cleaned or looks_sensitive(cleaned):
            return {"action": "SKIP", "type": "procedural", "text": "sensitive detail was not saved"}
        rows = self.db.scalars(select(TravelerRule).where(TravelerRule.user_id == self.user_id)).all()
        if any(row.rule.lower() == cleaned.lower() for row in rows):
            return {"action": "SKIP", "type": "procedural", "text": cleaned}
        self.db.add(TravelerRule(user_id=self.user_id, rule=cleaned, added=_today()))
        self.db.commit()
        return {"action": "ADD", "type": "procedural", "text": cleaned}

    def all_rules(self) -> list[str]:
        rows = self.db.scalars(
            select(TravelerRule).where(TravelerRule.user_id == self.user_id).order_by(TravelerRule.added, TravelerRule.id)
        )
        return [row.rule for row in rows]

    def recall(self, question: str) -> str:
        facts, rules = self.all_facts(), self.all_rules()
        try:
            episodes = self.search_episodes(question, n=2)
        except Exception:
            episodes = []
        if not (facts or rules or episodes):
            return "Nothing saved yet. This is a new traveller."
        lines = []
        if facts:
            lines.append("Facts about this traveller (semantic):")
            lines += [f"- {key}: {value}" for key, value in facts.items()]
        if episodes:
            lines.append("Related past trips (episodic):")
            lines += [f"- {item}" for item in episodes]
        if rules:
            lines.append("How to plan for this traveller (procedural):")
            lines += [f"- {rule}" for rule in rules]
        return "\n".join(lines)

    def snapshot(self) -> dict:
        return {"facts": self.all_facts(), "episodes": self.all_episodes(), "rules": self.all_rules()}

    def forget_everything(self) -> None:
        for row in self.db.scalars(select(TravelerFact).where(TravelerFact.user_id == self.user_id)):
            self.db.delete(row)
        for row in self.db.scalars(select(TravelerRule).where(TravelerRule.user_id == self.user_id)):
            self.db.delete(row)
        self.db.commit()
        try:
            _episodes().delete(where={"user_id": str(self.user_id)})
        except Exception:
            pass


def transcript_of(messages: list[dict]) -> str:
    who = {"user": "Traveller", "assistant": "TripWise"}
    return "\n".join(f"{who.get(item['role'], item['role'])}: {text_of(item['content'])}" for item in messages)


def extract_memories(messages: list[dict], memory: UserMemory, llm) -> list[MemoryItem]:
    try:
        chain = EXTRACT_PROMPT | llm.with_structured_output(MemoryList)
        result = chain.invoke({"existing": str(memory.snapshot()), "transcript": transcript_of(messages)})
        return list(result.memories)
    except Exception:
        raw = llm.invoke(EXTRACT_PROMPT.format_messages(
            existing=str(memory.snapshot()),
            transcript=transcript_of(messages) + "\n\nReply as JSON: {\"memories\": [{\"type\": \"semantic\", \"key\": \"group_size\", \"content\": \"...\"}]}",
        ))
        text = getattr(raw, "content", "") or ""
        if isinstance(text, list):
            text = " ".join(str(part) for part in text)
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            return []
        return MemoryList.model_validate_json(text[start : end + 1]).memories


def store_memories(items: list[MemoryItem], memory: UserMemory) -> list[dict]:
    report = []
    for item in items:
        if item.type == "semantic":
            report.append(memory.set_fact(item.key, item.content))
        elif item.type == "episodic":
            report.append(memory.add_episode(item.content))
        else:
            report.append(memory.add_rule(item.content))
    return report


def save_session(messages: list[dict], memory: UserMemory, llm) -> dict:
    if not messages:
        return {"report": [], "memory": memory.snapshot()}
    items = extract_memories(messages, memory, llm)
    report = store_memories(items, memory)
    return {"report": report, "memory": memory.snapshot()}
