import os
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.database.connection import get_db
from app.filters import genuine_airline_clause
from app.models.airport import Airport
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route
from app.schemas.flight import FlightSearchResponse, FlightSearchResult
from app.services.cache import (
    build_search_cache_key,
    cache_search_result,
    get_cached_search_result,
)
from app.services.mock_data import ensure_mock_route_data

router = APIRouter(
    prefix="/api",
    tags=["Search"],
)


@router.get("/search", response_model=FlightSearchResponse)
def search_flights(
    source: str = Query(..., min_length=1),
    destination: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort: Literal["price"] = "price",
    order: Literal["asc", "desc"] = "asc",
    db: Session = Depends(get_db),
):
    """Search active routes by origin/destination IATA codes.

    Each result carries the flight's latest recorded price snapshot.
    """
    normalized_source = source.strip().upper()
    normalized_destination = destination.strip().upper()
    if os.getenv("DEMO_ON_DEMAND_ROUTES", "false").lower() == "true":
        ensure_mock_route_data(normalized_source, normalized_destination)
    cache_key = build_search_cache_key(
        normalized_source,
        normalized_destination,
        page,
        limit,
        sort,
        order,
    )
    cached_result = get_cached_search_result(cache_key)
    if cached_result is not None:
        return cached_result

    origin_airport = aliased(Airport)
    destination_airport = aliased(Airport)

    route_filters = [
        origin_airport.iata_code == normalized_source,
        destination_airport.iata_code == normalized_destination,
        Route.active.is_(True),
        genuine_airline_clause(Flight.airline),
    ]

    total = (
        db.query(func.count(Flight.id))
        .join(Route, Flight.route_id == Route.id)
        .join(origin_airport, Route.origin_airport == origin_airport.id)
        .join(destination_airport, Route.destination_airport == destination_airport.id)
        .filter(*route_filters)
        .scalar()
    )

    # Latest snapshot per flight: the highest id is the most recent insert.
    latest_snapshot = (
        db.query(
            PriceSnapshot.flight_id.label("flight_id"),
            func.max(PriceSnapshot.id).label("snapshot_id"),
        )
        .filter(PriceSnapshot.source != "synthetic")
        .group_by(PriceSnapshot.flight_id)
        .subquery()
    )

    price_order = (
        PriceSnapshot.price.desc() if order == "desc" else PriceSnapshot.price.asc()
    )

    rows = (
        db.query(
            Flight,
            PriceSnapshot,
            origin_airport.iata_code,
            destination_airport.iata_code,
        )
        .join(Route, Flight.route_id == Route.id)
        .join(origin_airport, Route.origin_airport == origin_airport.id)
        .join(destination_airport, Route.destination_airport == destination_airport.id)
        .outerjoin(latest_snapshot, latest_snapshot.c.flight_id == Flight.id)
        .outerjoin(PriceSnapshot, PriceSnapshot.id == latest_snapshot.c.snapshot_id)
        .filter(*route_filters)
        .order_by(price_order.nulls_last())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    result = {
        "flights": [
            FlightSearchResult(
                id=flight.id,
                route_id=flight.route_id,
                airline=flight.airline,
                flight_number=flight.flight_number,
                departure_time=flight.departure_time,
                arrival_time=flight.arrival_time,
                source=origin_code,
                destination=destination_code,
                price=snapshot.price if snapshot else None,
                currency=snapshot.currency if snapshot else None,
            ).model_dump(mode="json")
            for flight, snapshot, origin_code, destination_code in rows
        ],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }
    cache_search_result(cache_key, result)
    return result