"""SQLite by default. The same models target PostgreSQL when NPS_DATABASE_URL is a Postgres URL."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import database_url
from app.db.models import Base

_engine = None
_factory = None


def get_engine():
    global _engine, _factory
    url = database_url()
    if _engine is None or str(_engine.url) != url:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        _factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def session_factory():
    get_engine()
    return _factory


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def reset_engine():
    """Drop the cached engine so tests can point at a new database URL."""
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _factory = None
