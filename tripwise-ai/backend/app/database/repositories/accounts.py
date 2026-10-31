import json
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database.models import ChatMessage, ChatSession, Itinerary, Trip, User, utcnow


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_email(self, email: str) -> User | None:
        return self.db.scalars(select(User).where(User.email == email.strip().lower())).first()

    def by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def create(self, name: str, email: str, password_hash: str, role: str = "user") -> User:
        user = User(name=name.strip(), email=email.strip().lower(), password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.created_at.desc())))

    def set_role(self, user_id: int, role: str) -> User | None:
        user = self.by_id(user_id)
        if not user:
            return None
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


class TripRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: int) -> list[Trip]:
        stmt = (
            select(Trip)
            .where(Trip.user_id == user_id)
            .options(selectinload(Trip.days), selectinload(Trip.destination))
            .order_by(Trip.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_for_user(self, trip_id: int, user_id: int) -> Trip | None:
        stmt = (
            select(Trip)
            .where(Trip.id == trip_id, Trip.user_id == user_id)
            .options(selectinload(Trip.days), selectinload(Trip.destination))
        )
        return self.db.scalars(stmt).first()

    def create(self, user_id: int, **fields) -> Trip:
        trip = Trip(user_id=user_id, **fields)
        self.db.add(trip)
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def update(self, trip: Trip, **fields) -> Trip:
        for key, value in fields.items():
            if value is not None and hasattr(trip, key):
                setattr(trip, key, value)
        trip.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def replace_days(self, trip: Trip, days: list[dict]) -> Trip:
        for existing in list(trip.days):
            self.db.delete(existing)
        self.db.flush()
        for day in days:
            self.db.add(
                Itinerary(
                    trip_id=trip.id,
                    day_number=day["day_number"],
                    title=day["title"],
                    activities_json=json.dumps(day["activities"]),
                    estimated_cost=day["estimated_cost"],
                )
            )
        self.db.commit()
        self.db.refresh(trip)
        return self.get_for_user(trip.id, trip.user_id)


def serialize_day(day: Itinerary) -> dict:
    try:
        activities = json.loads(day.activities_json or "{}")
    except json.JSONDecodeError:
        activities = {}
    return {
        "id": day.id,
        "trip_id": day.trip_id,
        "day_number": day.day_number,
        "title": day.title,
        "activities": activities,
        "estimated_cost": float(day.estimated_cost or 0),
        "price_label": "demonstration_estimate",
    }


def serialize_trip(trip: Trip) -> dict:
    try:
        estimate = json.loads(trip.estimate_json or "{}")
    except json.JSONDecodeError:
        estimate = {}
    try:
        preferences = json.loads(trip.preferences_json or "{}")
    except json.JSONDecodeError:
        preferences = {}
    return {
        "id": trip.id,
        "title": trip.title,
        "origin": trip.origin,
        "destination_id": trip.destination_id,
        "destination_name": trip.destination.name if trip.destination else None,
        "destination_slug": trip.destination.slug if trip.destination else None,
        "image_url": trip.destination.image_url if trip.destination else "",
        "start_date": trip.start_date.isoformat() if isinstance(trip.start_date, date) else None,
        "end_date": trip.end_date.isoformat() if isinstance(trip.end_date, date) else None,
        "traveler_count": trip.traveler_count,
        "adults": trip.adults,
        "children": trip.children,
        "budget": float(trip.budget or 0),
        "status": trip.status,
        "preferences": preferences,
        "estimate": estimate,
        "days": [serialize_day(day) for day in sorted(trip.days, key=lambda item: item.day_number)],
        "created_at": trip.created_at.isoformat() if isinstance(trip.created_at, datetime) else None,
    }


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_sessions(self, user_id: int) -> list[ChatSession]:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
        return list(self.db.scalars(stmt))

    def get_session(self, session_id: int, user_id: int) -> ChatSession | None:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        return self.db.scalars(stmt).first()

    def create_session(self, user_id: int, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, session_title=title[:180] or "New trip")
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def add_message(self, session: ChatSession, role: str, content: str, metadata: dict | None = None) -> ChatMessage:
        message = ChatMessage(
            session_id=session.id,
            role=role,
            content=content,
            metadata_json=json.dumps(metadata or {}),
        )
        session.updated_at = utcnow()
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def delete_session(self, session: ChatSession) -> None:
        self.db.delete(session)
        self.db.commit()


def serialize_message(message: ChatMessage) -> dict:
    try:
        metadata = json.loads(message.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "metadata": metadata,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def serialize_session(session: ChatSession, with_messages: bool = False) -> dict:
    payload = {
        "id": session.id,
        "session_title": session.session_title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }
    if with_messages:
        payload["messages"] = [serialize_message(item) for item in session.messages]
    return payload


class StatsRepository:
    def __init__(self, db: Session):
        self.db = db

    def counts(self) -> dict:
        from app.database.models import Destination, KnowledgeDocument

        def count(model) -> int:
            return int(self.db.scalar(select(func.count()).select_from(model)) or 0)

        return {
            "users": count(User),
            "destinations": count(Destination),
            "trips": count(Trip),
            "itineraries": count(Itinerary),
            "knowledge_documents": count(KnowledgeDocument),
        }
