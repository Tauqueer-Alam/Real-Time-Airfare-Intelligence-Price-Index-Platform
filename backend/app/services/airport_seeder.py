"""Populate the airports table from the bundled dataset at startup."""
import logging

from sqlalchemy.exc import SQLAlchemyError

from app.data.airports import AIRPORTS

logger = logging.getLogger(__name__)


def seed_airports() -> None:
    """Insert airports from the bundled dataset that are missing in the database.

    Idempotent: existing IATA codes are kept untouched, only new codes are added.
    """
    from app.database.connection import SessionLocal

    from app.models.airport import Airport

    db = SessionLocal()
    try:
        existing_codes = {code for (code,) in db.query(Airport.iata_code).all()}
        new_airports = [
            Airport(
                iata_code=entry["iata"],
                name=entry["name"],
                city=entry["city"],
                country=entry["country"],
            )
            for entry in AIRPORTS
            if entry["iata"] not in existing_codes
        ]
        if new_airports:
            db.add_all(new_airports)
            db.commit()
            logger.info("Seeded %d airports into the database", len(new_airports))
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to seed the airports table")
    finally:
        db.close()