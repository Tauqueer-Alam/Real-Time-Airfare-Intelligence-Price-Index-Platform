"""Airport autocomplete search endpoint backed by the airports table."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.airport import Airport

router = APIRouter(
    prefix="/api",
    tags=["Airports"],
)


@router.get("/airports")
def get_airports(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(10, ge=1, le=25),
    db: Session = Depends(get_db),
):
    """Search airports by IATA code, name, city, or country.

    Returns matching airports with their IATA code, full name, city,
    and country so the frontend can show a dropdown suggestion list.
    Exact IATA code matches are ranked first.
    """
    term = q.strip().lower()
    if not term:
        return {"airports": [], "total": 0}

    pattern = f"%{term}%"

    priority = case(
        (func.lower(Airport.iata_code) == term, 0),
        (func.lower(Airport.iata_code).like(f"{term}%"), 1),
        (func.lower(Airport.name).like(pattern), 2),
        (func.lower(Airport.city).like(pattern), 3),
        (func.lower(Airport.country).like(pattern), 4),
        else_=5,
    )

    matches = (
        db.query(Airport)
        .filter(
            or_(
                func.lower(Airport.iata_code).like(pattern),
                func.lower(Airport.name).like(pattern),
                func.lower(Airport.city).like(pattern),
                func.lower(Airport.country).like(pattern),
            )
        )
        .order_by(priority, Airport.iata_code)
        .limit(limit)
        .all()
    )

    return {
        "airports": [
            {
                "id": airport.id,
                "iata_code": airport.iata_code,
                "name": airport.name,
                "city": airport.city,
                "country": airport.country,
            }
            for airport in matches
        ],
        "total": len(matches),
    }