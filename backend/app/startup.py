"""Initialize the database with demo data before starting the API."""
from __future__ import annotations

import logging
import os
import sys

from app.database.connection import Base, SessionLocal, engine
from app.models.airport import Airport
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route
from app.models.user import User
from app.services.airport_seeder import seed_airports
from app.services.mock_data import seed_mock_route_data
from app.services.synthetic_history import generate_synthetic_history

logger = logging.getLogger(__name__)


def initialize_database() -> None:
    """Create tables and populate the deployment demo dataset once per startup."""
    Base.metadata.create_all(bind=engine)
    seed_airports()
    seed_mock_route_data(force=False)

    if "test_airfare.db" in os.getenv("DATABASE_URL", "").lower():
        return

    db = SessionLocal()
    try:
        inserted = generate_synthetic_history(db)
        logger.info("Inserted %d synthetic historical snapshots", inserted)
    finally:
        db.close()


def create_database_schema() -> None:
    """Create empty tables quickly so the web process can bind its port."""
    Base.metadata.create_all(bind=engine)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    create_database_schema()
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            os.getenv("PORT", "8000"),
        ],
    )


if __name__ == "__main__":
    main()
