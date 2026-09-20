from datetime import datetime, timezone

from app.database.connection import SessionLocal
from app.models.price_snapshot import PriceSnapshot
from app.services.synthetic_history import generate_synthetic_history


def test_synthetic_history_is_realistic_idempotent_and_source_labeled(
    client, sample_flight
):
    now = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)
    db = SessionLocal()
    try:
        first_inserted = generate_synthetic_history(
            db,
            days=30,
            route="DEL-BLR",
            snapshots_per_day=4,
            now=now,
        )
        second_inserted = generate_synthetic_history(
            db,
            days=30,
            route="DEL-BLR",
            snapshots_per_day=4,
            now=now,
        )
        rows = (
            db.query(PriceSnapshot)
            .filter(
                PriceSnapshot.flight_id == sample_flight["id"],
                PriceSnapshot.source == "synthetic",
            )
            .all()
        )
    finally:
        db.close()

    assert first_inserted == 120
    assert second_inserted == 0
    assert len(rows) == 120
    assert all(row.price > 0 for row in rows)
    assert {row.source for row in rows} == {"synthetic"}
    timestamps = [row.recorded_at for row in rows]
    assert min(timestamps).date().isoformat() == "2026-08-20"
    assert max(timestamps).date().isoformat() == "2026-09-18"
    assert len({timestamp.date() for timestamp in timestamps}) == 30
    assert max(row.price for row in rows) / min(row.price for row in rows) < 1.6


def test_synthetic_history_excludes_zz_and_keeps_live_search_separate(
    client, sample_route, sample_flight
):
    zz_flight = client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "Placeholder Carrier (ZZ)",
            "flight_number": "ZZ 100",
            "departure_time": "2026-09-20T10:00:00",
        },
    ).json()
    client.post(
        f"/api/flights/{sample_flight['id']}/prices",
        json={"price": 7777, "source": "flightapi"},
    )

    db = SessionLocal()
    try:
        inserted = generate_synthetic_history(
            db,
            days=2,
            route="DEL-BLR",
            snapshots_per_day=2,
            now=datetime(2026, 9, 19, 12, tzinfo=timezone.utc),
        )
        zz_rows = (
            db.query(PriceSnapshot)
            .filter(PriceSnapshot.flight_id == zz_flight["id"])
            .count()
        )
    finally:
        db.close()

    response = client.get("/api/search?source=DEL&destination=BLR")
    assert inserted == 4
    assert zz_rows == 0
    assert response.status_code == 200
    assert response.json()["flights"][0]["price"] == 7777


def test_synthetic_history_feeds_baseline_and_is_reported_as_synthetic(
    client, sample_flight
):
    client.post(
        f"/api/flights/{sample_flight['id']}/prices",
        json={"price": 6000, "source": "flightapi"},
    )
    db = SessionLocal()
    try:
        generate_synthetic_history(
            db,
            days=30,
            route="DEL-BLR",
            snapshots_per_day=2,
            now=datetime(2026, 9, 19, 12, tzinfo=timezone.utc),
        )
    finally:
        db.close()

    index_response = client.get("/api/analytics/price-index?source=DEL&destination=BLR")
    history_response = client.get(
        "/api/analytics/price-history?source=DEL&destination=BLR&days=30"
    )

    assert index_response.status_code == 200
    assert index_response.json()["historical_source"] == "synthetic"
    assert index_response.json()["baseline_price"] > 0
    assert history_response.status_code == 200
    assert history_response.json()["historical_source"] == "mixed"
    assert history_response.json()["granularity"] == "daily"
    assert len(history_response.json()["history"]) == 30
