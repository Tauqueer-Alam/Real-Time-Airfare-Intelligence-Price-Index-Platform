import os

os.environ["DATABASE_URL"] = "sqlite:///./test_airfare.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-local-pytest-runs"

import pytest
from fastapi.testclient import TestClient

from app.database.connection import Base, SessionLocal, engine
from app.main import app
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route
from app.models.user import User
from app.services.airport_seeder import seed_airports


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """Recreate the schema so a stale test DB can never keep old tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_airports()
    yield


@pytest.fixture(autouse=True)
def reset_database():
    """Clear transactional tables before and after each test.

    Airports are reference data seeded once per session, so they are kept.
    """
    db = SessionLocal()
    try:
        for model in (PriceSnapshot, Flight, Route, User):
            db.query(model).delete()
        db.commit()
    finally:
        db.close()

    yield

    db = SessionLocal()
    try:
        for model in (PriceSnapshot, Flight, Route, User):
            db.query(model).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    test_client = TestClient(app)
    register_response = test_client.post(
        "/api/auth/register",
        json={
            "name": "Fixture User",
            "email": "fixture@example.com",
            "password": "strongpassword123",
        },
    )
    assert register_response.status_code == 201
    login_response = test_client.post(
        "/api/auth/login",
        json={
            "email": "fixture@example.com",
            "password": "strongpassword123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


@pytest.fixture
def sample_route(client):
    response = client.post(
        "/api/routes/",
        json={"origin": "DEL", "destination": "BLR"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def sample_flight(client, sample_route):
    response = client.post(
        "/api/flights/",
        json={
            "route_id": sample_route["id"],
            "airline": "IndiGo",
            "flight_number": "6E 234",
            "departure_time": "2026-09-20T10:30:00",
            "arrival_time": "2026-09-20T13:00:00",
        },
    )
    assert response.status_code == 201
    return response.json()