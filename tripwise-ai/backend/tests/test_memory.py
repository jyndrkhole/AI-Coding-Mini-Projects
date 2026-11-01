import asyncio
import hashlib

from fastapi.testclient import TestClient

from app.a2a.client import ask_local_guide
from app.a2a.guide import guide_brain, notes_for
from app.ai.memory import UserMemory
from app.core.config import get_settings
from app.core.security import hash_password
from app.database.connection import SessionLocal, init_db
from app.database.models import User
from app.main import app


class FakeEmbed:
    def embed_query(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [byte / 255 for byte in digest[:16]]


def _user(db, email: str) -> User:
    row = User(name=email.split("@")[0], email=email, password_hash=hash_password("Tripwise#Travel1"), role="user")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_memory_updates_skips_and_stays_private():
    init_db()
    db = SessionLocal()
    try:
        asha = _user(db, "memory-asha@example.com")
        nia = _user(db, "memory-nia@example.com")
        asha_memory = UserMemory(db, asha.id, embed=FakeEmbed())
        nia_memory = UserMemory(db, nia.id, embed=FakeEmbed())

        assert "Nothing saved yet" in asha_memory.recall("goa")
        added = asha_memory.set_fact("group_size", "4 friends")
        assert added["action"] == "ADD"
        same = asha_memory.set_fact("group_size", "4 friends")
        assert same["action"] == "SKIP"
        changed = asha_memory.set_fact("group_size", "5 friends")
        assert changed["action"] == "UPDATE"
        assert changed["old"] == "4 friends"

        secret = asha_memory.set_fact("note", "my password is hunter2")
        assert secret["action"] == "SKIP"
        card = asha_memory.add_rule("card number 4111111111111111")
        assert card["action"] == "SKIP"

        rule = asha_memory.add_rule("Prefer vegetarian food")
        assert rule["action"] == "ADD"
        assert asha_memory.add_rule("prefer vegetarian food")["action"] == "SKIP"

        first = asha_memory.add_episode("We went to Goa in March and liked the quieter beaches.")
        assert first["action"] == "ADD"
        assert asha_memory.add_episode("We went to Goa in March and liked the quieter beaches.")["action"] == "SKIP"

        recalled = asha_memory.recall("beach trip")
        assert "group_size: 5 friends" in recalled
        assert "Prefer vegetarian food" in recalled
        assert "quieter beaches" in recalled
        assert "Nothing saved yet" in nia_memory.recall("beach trip")

        asha_memory.forget_everything()
        assert "Nothing saved yet" in asha_memory.recall("beach trip")
        assert nia_memory.all_facts() == {}
    finally:
        db.close()


def test_memory_routes_are_user_scoped():
    with TestClient(app) as client:
        registered = client.post(
            "/api/auth/register",
            json={"name": "Memory User", "email": "memory-route@example.com", "password": "Tripwise#Travel1"},
        )
        token = registered.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        loaded = client.get("/api/advisor/memory", headers=headers)
        assert loaded.status_code == 200
        assert loaded.json()["data"]["facts"] == {}
        cleared = client.delete("/api/advisor/memory", headers=headers)
        assert cleared.status_code == 200
        assert cleared.json()["data"]["episodes"] == []


def test_local_guide_notes_and_offline_client():
    assert "Matanga" in notes_for("What should we do in Hampi in December?")
    assert notes_for("What about Paris?") == "No notes for this place."
    answer = asyncio.run(guide_brain("What should we do in Hampi in December?"))
    assert "Matanga" in answer or "Virupaksha" in answer

    settings = get_settings()
    previous = settings.guide_url
    settings.guide_url = "http://127.0.0.1:9"
    try:
        text = asyncio.run(ask_local_guide("Hampi", "December"))
    finally:
        settings.guide_url = previous
    assert "offline" in text.lower()
