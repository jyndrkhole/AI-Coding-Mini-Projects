"""Normalized SQLite schema. Structured prices and records live here, not in ChromaDB."""

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trips: Mapped[list["Trip"]] = relationship(back_populates="user")
    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")


class Destination(Base):
    __tablename__ = "destinations"
    __table_args__ = (
        Index("ix_destinations_type", "destination_type"),
        Index("ix_destinations_state", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    travel_mode: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="India")
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    destination_type: Mapped[str] = mapped_column(String(40), nullable=False)
    best_season: Mapped[str] = mapped_column(String(120), nullable=False)
    best_months: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    ideal_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_min: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    budget_max: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    demo_travel_cost_per_person: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    demo_daily_spend_per_person: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    family_fit: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    couple_fit: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    adventure_fit: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    pros: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cons: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    accommodations: Mapped[list["Accommodation"]] = relationship(back_populates="destination", cascade="all, delete-orphan")
    attractions: Mapped[list["Attraction"]] = relationship(back_populates="destination", cascade="all, delete-orphan")
    tips: Mapped[list["TravelTip"]] = relationship(back_populates="destination", cascade="all, delete-orphan")


class Accommodation(Base):
    __tablename__ = "accommodations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    accommodation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_per_night: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    amenities: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(160), nullable=False, default="demonstration")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    destination: Mapped[Destination] = relationship(back_populates="accommodations")


class Attraction(Base):
    __tablename__ = "attractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="sightseeing")
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    ideal_duration: Mapped[str] = mapped_column(String(40), nullable=False, default="2 hours")
    best_time_to_visit: Mapped[str] = mapped_column(String(80), nullable=False, default="morning")
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    destination: Mapped[Destination] = relationship(back_populates="attractions")


class TravelTip(Base):
    __tablename__ = "travel_tips"
    __table_args__ = (Index("ix_travel_tips_destination", "destination_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_id: Mapped[int | None] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    season: Mapped[str] = mapped_column(String(40), nullable=False, default="any")
    source: Mapped[str] = mapped_column(String(160), nullable=False, default="demonstration")

    destination: Mapped[Destination | None] = relationship(back_populates="tips")


class TravelLink(Base):
    """Origin-to-destination facts such as 'near Pune'. The model does not guess distance."""

    __tablename__ = "travel_links"
    __table_args__ = (UniqueConstraint("origin_city", "destination_id", name="uq_travel_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin_city: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    typical_hours: Mapped[float] = mapped_column(Numeric(6, 1), nullable=False)
    typical_cost_per_person: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    destination: Mapped[Destination] = relationship()


class DestinationNearby(Base):
    __tablename__ = "destination_nearby"
    __table_args__ = (UniqueConstraint("destination_id", "nearby_id", name="uq_nearby"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    nearby_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str] = mapped_column(String(200), nullable=False, default="")


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    destination_id: Mapped[int | None] = mapped_column(ForeignKey("destinations.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    origin: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    traveler_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    adults: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    children: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    budget: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    preferences_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    estimate_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="trips")
    destination: Mapped[Destination | None] = relationship()
    days: Mapped[list["Itinerary"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class Itinerary(Base):
    __tablename__ = "itineraries"
    __table_args__ = (UniqueConstraint("trip_id", "day_number", name="uq_trip_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    activities_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    trip: Mapped[Trip] = relationship(back_populates="days")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_title: Mapped[str] = mapped_column(String(180), nullable=False, default="New trip")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False, default="upload")
    document_type: Mapped[str] = mapped_column(String(20), nullable=False, default="md")
    destination: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="India")
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="guide")
    travel_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    season: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    ingestion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SavedDestination(Base):
    __tablename__ = "saved_destinations"
    __table_args__ = (UniqueConstraint("user_id", "destination_id", name="uq_saved_destination"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    destination: Mapped[Destination] = relationship()
