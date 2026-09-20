from __future__ import annotations

import random
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.data.airports import AIRPORTS
from app.models.airport import Airport
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route

PRIMARY_HUBS = [
    "DEL",
    "BLR",
    "BOM",
    "MAA",
    "HYD",
    "CCU",
    "DXB",
    "SIN",
    "LHR",
    "JFK",
    "BKK",
    "SYD",
    "JNB",
]

DEFAULT_MOCK_ROUTE_PAIRS = [
    ("DEL", "BLR"),
    ("DEL", "BOM"),
    ("BLR", "BOM"),
    ("BOM", "DEL"),
    ("BLR", "DEL"),
    ("MAA", "DEL"),
    ("DEL", "MAA"),
    ("HYD", "DEL"),
    ("DEL", "HYD"),
    ("HYD", "BLR"),
    ("BLR", "HYD"),
    ("CCU", "DEL"),
    ("DEL", "CCU"),
    ("DXB", "DEL"),
    ("DEL", "DXB"),
    ("SIN", "DEL"),
    ("DEL", "SIN"),
    ("LHR", "DEL"),
    ("DEL", "LHR"),
    ("JFK", "DEL"),
    ("DEL", "JFK"),
    ("BKK", "DEL"),
    ("DEL", "BKK"),
]


def build_mock_route_pairs() -> list[tuple[str, str]]:
    """Create a route graph that includes every airport in the catalog."""
    all_codes = sorted({entry["iata"].upper() for entry in AIRPORTS})
    pairs = list(DEFAULT_MOCK_ROUTE_PAIRS)
    seen = set(pairs)

    for index, code in enumerate(all_codes):
        for offset in range(1, 5):
            target = all_codes[(index + offset) % len(all_codes)]
            if target == code:
                continue
            for route in ((code, target), (target, code)):
                if route not in seen:
                    pairs.append(route)
                    seen.add(route)

        for hub in PRIMARY_HUBS:
            if hub == code or hub not in all_codes:
                continue
            for route in ((code, hub), (hub, code)):
                if route not in seen:
                    pairs.append(route)
                    seen.add(route)

    return pairs

AIRLINES = [
    "IndiGo",
    "Air India",
    "Vistara",
    "Akasa Air",
    "SpiceJet",
    "GoFirst",
    "Jet Airways",
    "Alliance Air",
]


def _airport_lookup(db: Session) -> dict[str, Airport]:
    airports = db.query(Airport).all()
    return {airport.iata_code: airport for airport in airports}


def _mock_price_for_route(source: str, destination: str, base: int) -> float:
    route_multiplier = {
        ("DEL", "BLR"): 1.00,
        ("DEL", "BOM"): 1.05,
        ("BLR", "BOM"): 0.94,
        ("BOM", "DEL"): 1.04,
        ("BLR", "DEL"): 0.96,
    }
    factor = route_multiplier.get((source, destination), 1.0)
    return round(base * factor * random.uniform(0.9, 1.18), 2)


def _route_flights_for_pair(source: str, destination: str) -> list[dict]:
    airlines = [
        ("IndiGo", "6E 234"),
        ("Air India", "AI 506"),
        ("Vistara", "UK 943"),
        ("Akasa Air", "QP 1362"),
    ]
    offset_minutes = [0, 120, 180, 240]

    flights: list[dict] = []
    for index, (airline, number) in enumerate(airlines):
        base_price = {
            ("DEL", "BLR"): 4300,
            ("DEL", "BOM"): 4700,
            ("BLR", "BOM"): 3900,
            ("BOM", "DEL"): 4500,
            ("BLR", "DEL"): 4200,
        }.get((source, destination), 5200 + index * 350)

        dep = datetime.now(timezone.utc).replace(hour=8 + index * 2, minute=offset_minutes[index] % 60, second=0, microsecond=0)
        arr = dep + timedelta(hours=2, minutes=20 + index * 15)
        flights.append(
            {
                "airline": airline,
                "flight_number": number,
                "departure_time": dep,
                "arrival_time": arr,
                "base_price": base_price,
            }
        )
    return flights


def seed_mock_route_data(force: bool = False) -> int:
    """Ensure the database has a realistic route/flight snapshot dataset for local demo usage."""
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        if not force and db.query(Route).count() > 0:
            return 0

        airport_map = _airport_lookup(db)
        for entry in AIRPORTS:
            code = entry["iata"].upper()
            if code not in airport_map:
                airport = Airport(
                    iata_code=code,
                    name=entry["name"],
                    city=entry["city"],
                    country=entry["country"],
                )
                db.add(airport)
                db.flush()
                airport_map[code] = airport

        created_routes = 0
        created_snapshots = 0
        seen_routes: set[tuple[int, int]] = set()

        route_pairs = build_mock_route_pairs()
        route_limit = os.getenv("DEMO_ROUTE_LIMIT")
        if route_limit:
            try:
                route_pairs = route_pairs[: max(int(route_limit), len(DEFAULT_MOCK_ROUTE_PAIRS))]
            except ValueError:
                pass

        for source, destination in route_pairs:
            origin = airport_map.get(source.upper())
            destination_airport = airport_map.get(destination.upper())
            if not origin or not destination_airport:
                continue

            route_key = (origin.id, destination_airport.id)
            if route_key in seen_routes:
                continue
            seen_routes.add(route_key)

            existing_route = (
                db.query(Route)
                .filter(Route.origin_airport == origin.id, Route.destination_airport == destination_airport.id)
                .first()
            )
            if existing_route is None:
                route = Route(origin_airport=origin.id, destination_airport=destination_airport.id, active=True)
                db.add(route)
                db.flush()
                created_routes += 1
                route_record = route
            else:
                route_record = existing_route

            for flight_def in _route_flights_for_pair(source, destination):
                existing_flight = (
                    db.query(Flight)
                    .filter(
                        Flight.route_id == route_record.id,
                        Flight.airline == flight_def["airline"],
                        Flight.flight_number == flight_def["flight_number"],
                    )
                    .first()
                )

                if existing_flight is None:
                    flight = Flight(
                        route_id=route_record.id,
                        airline=flight_def["airline"],
                        flight_number=flight_def["flight_number"],
                        departure_time=flight_def["departure_time"].replace(tzinfo=None),
                        arrival_time=flight_def["arrival_time"].replace(tzinfo=None),
                    )
                    db.add(flight)
                    db.flush()
                else:
                    flight = existing_flight

                for day_offset in range(0, 18):
                    snapshot_time = datetime.now(timezone.utc) - timedelta(days=day_offset, hours=4)
                    price = _mock_price_for_route(source, destination, flight_def["base_price"])
                    if day_offset == 0:
                        price *= random.uniform(0.97, 1.08)
                    snapshot = PriceSnapshot(
                        flight_id=flight.id,
                        price=price,
                        currency="INR",
                        recorded_at=snapshot_time.replace(tzinfo=None),
                        source="mock",
                    )
                    db.add(snapshot)
                    created_snapshots += 1

        db.commit()
        return created_routes + created_snapshots
    finally:
        db.close()
