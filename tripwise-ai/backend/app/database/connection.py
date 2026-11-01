"""SQLite engine. Foreign keys are enforced on every connection. The file survives restarts."""

import threading
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine = None
_schema_ready = False
_schema_lock = threading.Lock()
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
    """Apply the Alembic revision once. An older create_all database is stamped, not rebuilt."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        engine = get_engine()
        SessionLocal.configure(bind=engine)
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import inspect

        from app.core.config import BACKEND_ROOT

        cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{get_settings().sqlite_file}")
        names = set(inspect(engine).get_table_names())
        if "users" in names and "alembic_version" not in names:
            command.stamp(cfg, "001_initial")
        command.upgrade(cfg, "head")
        _schema_ready = True


def get_db() -> Generator[Session, None, None]:
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine() -> None:
    """Used by tests that point SQLITE_PATH at a fresh file."""
    global _engine, _schema_ready
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _schema_ready = False
