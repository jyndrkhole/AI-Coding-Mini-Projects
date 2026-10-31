"""Create tables, seed destinations, and exit."""

from app.database.connection import SessionLocal, init_db
from app.services.seed import seed_if_empty


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    print("SQLite catalogue is ready.")


if __name__ == "__main__":
    main()
