"""Resolve airports by IATA code, creating records from the bundled dataset."""
from sqlalchemy.orm import Session

from app.data.airports import AIRPORTS
from app.models.airport import Airport

_DATASET_BY_IATA = {entry["iata"].upper(): entry for entry in AIRPORTS}


def get_or_create_airport(db: Session, iata_code: str) -> Airport:
    """Return the airport for ``iata_code``, creating it from bundled data if needed."""
    code = iata_code.strip().upper()
    airport = db.query(Airport).filter(Airport.iata_code == code).first()
    if airport is not None:
        return airport

    dataset_entry = _DATASET_BY_IATA.get(code, {})
    airport = Airport(
        iata_code=code,
        name=dataset_entry.get("name", f"{code} Airport"),
        city=dataset_entry.get("city", "Unknown"),
        country=dataset_entry.get("country", "Unknown"),
    )
    db.add(airport)
    db.flush()
    return airport


def get_route_airport_pair(db: Session, origin_code: str, destination_code: str) -> tuple[Airport, Airport]:
    """Resolve (and create if missing) both airports of a route."""
    return (
        get_or_create_airport(db, origin_code),
        get_or_create_airport(db, destination_code),
    )