def test_frontend_routes_are_served_from_root(client):
    root_response = client.get("/")
    dashboard_response = client.get("/dashboard")
    docs_response = client.get("/docs")

    assert root_response.status_code == 200
    assert "Flight Search" in root_response.text
    assert dashboard_response.status_code == 404
    assert docs_response.status_code == 200


def test_seed_mock_data_creates_realistic_fares_for_default_routes(client):
    from app.services.mock_data import seed_mock_route_data
    from app.data.airports import AIRPORTS
    from app.database.connection import SessionLocal
    from app.models.route import Route
    from app.models.price_snapshot import PriceSnapshot
    from app.models.airport import Airport

    seed_mock_route_data(force=True)

    db = SessionLocal()
    try:
        route_count = db.query(Route).count()
        snapshot_count = db.query(PriceSnapshot).count()
        airport_codes = {code for (code,) in db.query(Airport.iata_code).all()}
        route_airports = {
            code
            for code, _ in db.query(Airport.iata_code, Route.id)
            .join(Route, Route.origin_airport == Airport.id)
            .all()
        } | {
            code
            for code, _ in db.query(Airport.iata_code, Route.id)
            .join(Route, Route.destination_airport == Airport.id)
            .all()
        }
    finally:
        db.close()

    assert route_count >= 100
    assert snapshot_count >= 400
    assert len(route_airports) >= len(AIRPORTS)


def test_get_flights_returns_all_flights(client, sample_flight):
    response = client.get("/api/flights/")

    assert response.status_code == 200
    flights = response.json()
    assert len(flights) == 1
    assert flights[0]["airline"] == "IndiGo"
    assert flights[0]["flight_number"] == "6E 234"


def test_get_flights_excludes_non_genuine_airlines(client, sample_route):
    """The /api/flights/ endpoint must not return non-genuine airlines."""
    client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "Duffel Airways (DUFFEL)",
            "flight_number": "DA 100",
            "departure_time": "2026-09-20T10:00:00",
            "arrival_time": "2026-09-20T12:00:00",
        },
    )
    client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "Air India",
            "flight_number": "AI 506",
            "departure_time": "2026-09-20T14:00:00",
            "arrival_time": "2026-09-20T16:00:00",
        },
    )

    response = client.get("/api/flights/")

    assert response.status_code == 200
    flights = response.json()
    airlines = [flight["airline"] for flight in flights]
    assert "Duffel Airways (DUFFEL)" not in airlines
    assert "Air India" in airlines
    assert len(flights) == 1


def test_post_flight_creates_flight(client, sample_route):
    response = client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "Air India",
            "flight_number": "AI 506",
            "departure_time": "2026-09-21T08:00:00",
            "arrival_time": "2026-09-21T10:30:00",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["airline"] == "Air India"
    assert data["route_id"] == sample_route["id"]


def test_post_flight_rejects_unknown_route(client):
    response = client.post(
        "/api/flights/",
        json={
            "route_id": 999999,
            "airline": "Air India",
            "flight_number": "AI 506",
            "departure_time": "2026-09-21T08:00:00",
        },
    )

    assert response.status_code == 404


def test_get_flight_by_id_returns_single_flight(client, sample_flight):
    response = client.get(f"/api/flights/{sample_flight['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == sample_flight["id"]


def test_put_flight_updates_existing_flight(client, sample_flight):
    response = client.put(
        f"/api/flights/{sample_flight['id']}",
        json={"flight_number": "6E 999", "airline": "IndiGo Express"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["flight_number"] == "6E 999"
    assert data["airline"] == "IndiGo Express"


def test_delete_flight_removes_flight(client, sample_flight):
    delete_response = client.delete(f"/api/flights/{sample_flight['id']}")
    get_response = client.get(f"/api/flights/{sample_flight['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Flight deleted successfully"
    assert get_response.status_code == 404


def test_route_creation_is_idempotent(client):
    first = client.post("/api/routes/", json={"origin": "DEL", "destination": "BOM"})
    second = client.post("/api/routes/", json={"origin": "del", "destination": "bom"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["origin"]["iata_code"] == "DEL"
    assert first.json()["destination"]["iata_code"] == "BOM"


def test_route_creation_rejects_same_airport(client):
    response = client.post("/api/routes/", json={"origin": "DEL", "destination": "DEL"})

    assert response.status_code == 400


def test_flight_search_returns_matching_route(client, sample_flight):
    other_route = client.post(
        "/api/routes/", json={"origin": "DEL", "destination": "BOM"}
    ).json()
    client.post(
        "/api/flights/",
        json={
            "route_id": other_route["id"],
            "airline": "Vistara",
            "flight_number": "UK 943",
            "departure_time": "2026-09-21T09:00:00",
        },
    )
    client.post(f"/api/flights/{sample_flight['id']}/prices", json={"price": 4200})

    response = client.get(
        "/api/search?source=del&destination=blr&page=1&limit=10&sort=price&order=asc"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["flights"][0]["destination"] == "BLR"
    assert data["flights"][0]["price"] == 4200


def test_flight_search_orders_by_latest_price(client, sample_flight):
    competitor_route = client.post(
        "/api/routes/", json={"origin": "DEL", "destination": "BLR"}
    ).json()
    competitor = client.post(
        "/api/flights/",
        json={
            "route_id": competitor_route["id"],
            "airline": "Air India",
            "flight_number": "AI 506",
            "departure_time": "2026-09-21T08:00:00",
        },
    ).json()

    client.post(f"/api/flights/{sample_flight['id']}/prices", json={"price": 4800})
    client.post(f"/api/flights/{competitor['id']}/prices", json={"price": 3900})

    response = client.get(
        "/api/search?source=DEL&destination=BLR&page=1&limit=10&sort=price&order=asc"
    )

    assert response.status_code == 200
    prices = [flight["price"] for flight in response.json()["flights"]]
    assert prices == [3900, 4800]


def test_price_creation_adds_history_record(client, sample_flight):
    response = client.post(
        f"/api/flights/{sample_flight['id']}/prices",
        json={"price": 4250, "currency": "INR", "source": "flightapi"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["flight_id"] == sample_flight["id"]
    assert data["price"] == 4250
    assert data["currency"] == "INR"
    assert data["source"] == "flightapi"
    assert "recorded_at" in data


def test_price_history_returns_oldest_to_newest(client, sample_flight):
    client.post(f"/api/flights/{sample_flight['id']}/prices", json={"price": 4250})
    client.post(f"/api/flights/{sample_flight['id']}/prices", json={"price": 4350})

    response = client.get(f"/api/flights/{sample_flight['id']}/prices")

    assert response.status_code == 200
    prices = response.json()
    assert [price["price"] for price in prices] == [4250, 4350]


def test_price_index_calculates_route_average(client, sample_flight):
    from datetime import datetime, timedelta, timezone

    from app.database.connection import SessionLocal
    from app.models.price_snapshot import PriceSnapshot

    db = SessionLocal()
    try:
        db.add(
            PriceSnapshot(
                flight_id=sample_flight["id"],
                price=5000,
                recorded_at=datetime.now(timezone.utc).replace(tzinfo=None)
                - timedelta(days=2),
                source="flightapi",
            )
        )
        db.commit()
    finally:
        db.close()

    client.post(f"/api/flights/{sample_flight['id']}/prices", json={"price": 4000})
    client.post(f"/api/flights/{sample_flight['id']}/prices", json={"price": 6000})

    response = client.get("/api/analytics/price-index?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert data["current_average_price"] == 5000
    assert data["baseline_price"] == 5000
    assert data["price_index"] == 100
    assert data["percentage_change"] == 0


def test_airport_search_queries_database(client):
    response = client.get("/api/airports?q=del")

    assert response.status_code == 200
    airports = response.json()["airports"]
    assert airports
    assert airports[0]["iata_code"] == "DEL"
    assert airports[0]["city"] == "New Delhi"


def test_price_index_uses_30_day_history_baseline(client, sample_flight):
    from datetime import datetime, timedelta, timezone

    from app.database.connection import SessionLocal
    from app.models.price_snapshot import PriceSnapshot

    db = SessionLocal()
    try:
        db.add_all(
            [
                PriceSnapshot(
                    flight_id=sample_flight["id"],
                    price=4800,
                    recorded_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    - timedelta(days=10),
                    source="flightapi",
                ),
                PriceSnapshot(
                    flight_id=sample_flight["id"],
                    price=5200,
                    recorded_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    - timedelta(days=5),
                    source="flightapi",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    client.post(f"/api/flights/{sample_flight['id']}/prices", json={"price": 6000})

    response = client.get("/api/analytics/price-index?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert data["current_average_price"] == 6000
    assert data["baseline_price"] == 5000
    assert data["baseline_source"] == "history_30d"
    assert data["price_index"] == 120
    assert data["percentage_change"] == 20


def _insert_snapshots(flight_id, rows):
    """Insert PriceSnapshots with explicit recorded_at values (naive UTC)."""
    from app.database.connection import SessionLocal
    from app.models.price_snapshot import PriceSnapshot

    db = SessionLocal()
    try:
        db.add_all(
            [
                PriceSnapshot(
                    flight_id=flight_id,
                    price=price,
                    recorded_at=recorded_at,
                    source="flightapi",
                )
                for recorded_at, price in rows
            ]
        )
        db.commit()
    finally:
        db.close()


def test_price_history_buckets_multiple_airlines_at_same_timestamp(
    client, sample_flight
):
    """Several airlines recorded during one collection run form ONE bucket."""
    from datetime import datetime, timezone

    same_time = datetime.now(timezone.utc).replace(
        minute=10, second=0, microsecond=0, tzinfo=None
    )
    _insert_snapshots(
        sample_flight["id"],
        [(same_time, 7590), (same_time, 7689), (same_time, 9694)],
    )

    response = client.get("/api/analytics/price-history?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "hourly"
    assert len(data["history"]) == 1
    bucket = data["history"][0]
    assert bucket["snapshot_count"] == 3
    assert bucket["average_fare"] == round((7590 + 7689 + 9694) / 3, 2)
    assert bucket["minimum_fare"] == 7590
    assert bucket["maximum_fare"] == 9694


def test_price_history_buckets_multiple_timestamps_chronologically(
    client, sample_flight
):
    """One bucket per collection hour, sorted oldest to newest."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0)
    _insert_snapshots(
        sample_flight["id"],
        [
            (now - timedelta(hours=2), 8000),
            (now, 8200),
            (now - timedelta(hours=1), 8100),
        ],
    )

    response = client.get("/api/analytics/price-history?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "hourly"
    assert len(data["history"]) == 3
    timestamps = [point["timestamp"] for point in data["history"]]
    assert timestamps == sorted(timestamps)
    assert [point["average_fare"] for point in data["history"]] == [8000, 8100, 8200]


def test_price_history_aggregates_duplicate_timestamps(client, sample_flight):
    """Snapshots with exactly the same recorded_at are aggregated, not
    plotted as separate points (no vertical lines)."""
    from datetime import datetime, timezone

    exact_time = datetime.now(timezone.utc).replace(
        minute=20, second=15, microsecond=123000, tzinfo=None
    )
    _insert_snapshots(
        sample_flight["id"],
        [(exact_time, 5000), (exact_time, 7000)],
    )

    response = client.get("/api/analytics/price-history?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 1
    bucket = data["history"][0]
    assert bucket["snapshot_count"] == 2
    assert bucket["average_fare"] == 6000
    assert bucket["minimum_fare"] == 5000
    assert bucket["maximum_fare"] == 7000


def test_price_history_aggregates_daily_across_multiple_days(client, sample_flight):
    """History spanning multiple days is aggregated into daily buckets."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _insert_snapshots(
        sample_flight["id"],
        [
            (now - timedelta(days=2), 4000),
            (now - timedelta(days=2) + timedelta(hours=1), 6000),
            (now - timedelta(days=1), 5000),
        ],
    )

    response = client.get("/api/analytics/price-history?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "daily"
    assert len(data["history"]) == 2
    first_day, second_day = data["history"]
    assert first_day["average_fare"] == 5000
    assert first_day["minimum_fare"] == 4000
    assert first_day["maximum_fare"] == 6000
    assert first_day["snapshot_count"] == 2
    assert second_day["average_fare"] == 5000
    assert second_day["snapshot_count"] == 1


def test_price_history_empty_route_returns_empty_list(client, sample_flight):
    response = client.get("/api/analytics/price-history?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "hourly"
    assert data["history"] == []


def test_price_history_excludes_test_airline_zz(client, sample_route):
    """Snapshots from the excluded test airline (Duffel Airways ZZ) must
    never appear in the route price history."""
    from datetime import datetime, timezone

    excluded = client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "Duffel Airways (ZZ)",
            "flight_number": "ZZ 001",
            "departure_time": "2026-09-21T08:00:00",
        },
    ).json()
    genuine = client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "IndiGo",
            "flight_number": "6E 234",
            "departure_time": "2026-09-21T09:00:00",
        },
    ).json()

    recorded_at = datetime.now(timezone.utc).replace(
        minute=40, second=0, microsecond=0, tzinfo=None
    )
    _insert_snapshots(
        excluded["id"],
        [(recorded_at, 99999)],
    )
    _insert_snapshots(
        genuine["id"],
        [(recorded_at, 4500)],
    )

    response = client.get("/api/analytics/price-history?source=DEL&destination=BLR")

    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 1
    bucket = data["history"][0]
    assert bucket["snapshot_count"] == 1
    assert bucket["average_fare"] == 4500
    assert bucket["maximum_fare"] == 4500


def test_scheduler_collects_active_routes_from_database(client, sample_route):
    from app.services.collection_scheduler import get_active_route_pairs

    pairs = get_active_route_pairs()

    assert ("DEL", "BLR") in pairs


def test_collection_interval_hours_configuration(monkeypatch):
    from app.services.collection_scheduler import get_collection_interval_seconds

    monkeypatch.setenv("COLLECTION_INTERVAL_HOURS", "2")
    assert get_collection_interval_seconds() == 7200

    monkeypatch.delenv("COLLECTION_INTERVAL_HOURS")
    monkeypatch.setenv("MOCK_COLLECTION_INTERVAL_SECONDS", "180")
    assert get_collection_interval_seconds() == 180

    monkeypatch.delenv("MOCK_COLLECTION_INTERVAL_SECONDS")
    assert get_collection_interval_seconds() == 3 * 3600


def test_create_flight_requires_authentication(sample_route):
    from fastapi.testclient import TestClient

    from app.main import app

    anonymous = TestClient(app)
    response = anonymous.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "Air India",
            "flight_number": "AI 506",
            "departure_time": "2026-09-21T08:00:00",
            "arrival_time": "2026-09-21T10:30:00",
        },
    )

    assert response.status_code == 401


def test_authentication_registers_and_logs_in_user(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "strongpassword123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "strongpassword123",
        },
    )

    assert register_response.status_code == 201
    assert register_response.json()["email"] == "test@example.com"
    assert login_response.status_code == 200
    assert login_response.json()["token_type"] == "bearer"
    assert login_response.json()["access_token"]


def test_search_excludes_non_genuine_airlines(client, sample_route):
    """Flights with non-genuine airline names (e.g. 'Duffel Airways') must
    not appear in search results, even if they exist in the database."""
    # Create a non-genuine airline flight
    client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "Duffel Airways (DUFFEL)",
            "flight_number": "DA 100",
            "departure_time": "2026-09-20T10:00:00",
            "arrival_time": "2026-09-20T12:00:00",
        },
    )
    # Create a genuine airline flight on the same route
    client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "IndiGo",
            "flight_number": "6E 234",
            "departure_time": "2026-09-20T14:00:00",
            "arrival_time": "2026-09-20T16:00:00",
        },
    )

    response = client.get(
        "/api/search?source=DEL&destination=BLR&page=1&limit=10&sort=price&order=asc"
    )

    assert response.status_code == 200
    data = response.json()
    airlines = [flight["airline"] for flight in data["flights"]]
    assert "Duffel Airways (DUFFEL)" not in airlines
    assert "IndiGo" in airlines
    assert data["total"] == 1
