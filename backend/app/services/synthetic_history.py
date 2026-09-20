"""Deterministic synthetic historical fare generation for development demos."""
from __future__ import annotations

import hashlib
import math
import random
import re
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.filters import is_genuine_airline
from app.models.airport import Airport
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route

SYNTHETIC_SOURCE = "synthetic"
DEFAULT_DAYS = 30
DEFAULT_SNAPSHOTS_PER_DAY = 4
_ZZ_CODE_PATTERN = re.compile(r"(?:^|[\s(])ZZ(?:\)|$)", re.IGNORECASE)


def _stable_seed(*parts: object) -> int:
    value = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def _parse_route(route: str) -> tuple[str, str]:
    normalized = route.replace(",", "-").replace(" ", "")
    parts = [part.upper() for part in normalized.split("-") if part]
    if len(parts) != 2 or any(len(part) != 3 for part in parts):
        raise ValueError("route must use SOURCE-DESTINATION IATA codes")
    return parts[0], parts[1]


def _route_flights(
    db: Session, route: str | None
) -> list[tuple[Flight, str, str]]:
    from sqlalchemy.orm import aliased

    origin_airport = aliased(Airport)
    destination_airport = aliased(Airport)
    query = (
        db.query(Flight, origin_airport.iata_code, destination_airport.iata_code)
        .join(Route, Flight.route_id == Route.id)
        .join(origin_airport, Route.origin_airport == origin_airport.id)
        .join(destination_airport, Route.destination_airport == destination_airport.id)
        .filter(Route.active.is_(True))
        .order_by(Route.id, Flight.id)
    )
    if route:
        source, destination = _parse_route(route)
        query = query.filter(
            origin_airport.iata_code == source,
            destination_airport.iata_code == destination,
        )

    return [
        (flight, source, destination)
        for flight, source, destination in query.all()
        if is_genuine_airline(flight.airline)
        and _ZZ_CODE_PATTERN.search(flight.airline) is None
    ]


def _base_price(db: Session, flight: Flight, seed: int) -> float:
    latest_real = (
        db.query(PriceSnapshot.price)
        .filter(
            PriceSnapshot.flight_id == flight.id,
            PriceSnapshot.source != SYNTHETIC_SOURCE,
        )
        .order_by(PriceSnapshot.recorded_at.desc(), PriceSnapshot.id.desc())
        .first()
    )
    if latest_real is not None:
        return max(float(latest_real[0]), 500.0)
    return float(3500 + seed % 4500)


def generate_synthetic_history(
    db: Session,
    days: int = DEFAULT_DAYS,
    route: str | None = None,
    snapshots_per_day: int = DEFAULT_SNAPSHOTS_PER_DAY,
    now: datetime | None = None,
) -> int:
    """Insert a deterministic, idempotent synthetic history for existing flights.

    Only completed calendar days are generated. Existing rows, including all
    real/API rows, are never changed or deleted.
    """
    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    if snapshots_per_day < 1 or snapshots_per_day > 24:
        raise ValueError("snapshots_per_day must be between 1 and 24")

    current = now or datetime.now(timezone.utc)
    today = current.astimezone(timezone.utc).date()
    flights = _route_flights(db, route)
    inserted = 0

    for flight, source, destination in flights:
        flight_seed = _stable_seed(source, destination, flight.id, flight.airline)
        base_price = _base_price(db, flight, flight_seed)
        existing = {
            snapshot.recorded_at
            for snapshot in db.query(PriceSnapshot)
            .filter(
                PriceSnapshot.flight_id == flight.id,
                PriceSnapshot.source == SYNTHETIC_SOURCE,
            )
            .all()
        }
        randomizer = random.Random(flight_seed)
        daily_level = 1.0

        for day_offset in range(days, 0, -1):
            day = today - timedelta(days=day_offset)
            daily_level += randomizer.uniform(-0.018, 0.018)
            if randomizer.random() < 0.08:
                daily_level += randomizer.uniform(-0.08, 0.08)
            daily_level = min(max(daily_level, 0.82), 1.18)
            seasonal = 1 + 0.025 * math.sin(day_offset / 3.5)

            for slot in range(snapshots_per_day):
                hour = (24 * slot) // snapshots_per_day
                minute = (60 * ((24 * slot) % snapshots_per_day)) // snapshots_per_day
                recorded_at = datetime.combine(
                    day, time(hour=hour, minute=minute)
                )
                if recorded_at in existing:
                    continue

                snapshot_randomizer = random.Random(
                    _stable_seed(flight_seed, day.isoformat(), slot)
                )
                price = base_price * daily_level * seasonal
                price *= 1 + snapshot_randomizer.uniform(-0.025, 0.025)
                price = round(max(price, 250.0), 2)
                db.add(
                    PriceSnapshot(
                        flight_id=flight.id,
                        price=price,
                        currency="INR",
                        recorded_at=recorded_at,
                        source=SYNTHETIC_SOURCE,
                    )
                )
                existing.add(recorded_at)
                inserted += 1

    db.commit()
    return inserted
