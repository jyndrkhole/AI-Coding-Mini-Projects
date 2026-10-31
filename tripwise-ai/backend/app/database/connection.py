"""SQLite engine. Foreign keys are enforced on every connection. The file survives restarts."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.database.models import Base

_engine = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        settings.sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{settings.sqlite_file}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    SessionLocal.configure(bind=engine)


def get_db() -> Generator[Session, None, None]:
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine() -> None:
    """Used by tests that point SQLITE_PATH at a fresh file."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
