"""One-off demo: exercise the running API end to end and print results."""
import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method: str, path: str, payload: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def show(title: str, status: int, body):
    print(f"\n=== {title} [{status}] ===")
    print(json.dumps(body, indent=2)[:1800])


status, body = call("GET", "/")
show("Health", status, body)

status, body = call("GET", "/api/airports?q=del&limit=2")
show("Airport autocomplete (q=del)", status, body)

status, body = call("POST", "/api/routes", {"origin": "DEL", "destination": "BLR"})
show("Create route DEL->BLR", status, body)
route_id = body["id"]

flights = [
    ("IndiGo", "6E 234", "2026-09-20T10:30:00", "2026-09-20T13:05:00", 7420),
    ("Air India", "AI 506", "2026-09-20T08:15:00", "2026-09-20T10:50:00", 8050),
    ("Akasa Air", "QP 1362", "2026-09-20T15:40:00", "2026-09-20T18:20:00", 7780),
]
flight_ids = []
for airline, number, departure, arrival, price in flights:
    status, body = call(
        "POST",
        "/api/flights",
        {
            "route_id": route_id,
            "airline": airline,
            "flight_number": number,
            "departure_time": departure,
            "arrival_time": arrival,
        },
    )
    assert status == 201, body
    flight_ids.append(body["id"])
    status, body = call(
        "POST",
        f"/api/flights/{body['id']}/prices",
        {"price": price, "currency": "INR", "source": "demo"},
    )
    assert status == 201, body

print("\nCreated 3 flights with today's price snapshots.")

status, body = call("GET", "/api/search?source=DEL&destination=BLR&page=1&limit=10")
show("Search DEL->BLR (sorted by price)", status, body)

status, body = call("GET", "/api/analytics/price-index?source=DEL&destination=BLR")
show("Price index (30-day baseline)", status, body)

status, body = call("GET", "/api/analytics/price-history?source=DEL&destination=BLR&days=30")
show("Route price history (daily)", status, body)

status, body = call("GET", "/api/routes")
print(f"\n=== Routes now tracked in DB: {len(body)} ===")
for route in body:
    print(
        f"  #{route['id']} {route['origin']['iata_code']} -> "
        f"{route['destination']['iata_code']} (active={route['active']})"
    )
print("\nThe scheduler collects all of these every COLLECTION_INTERVAL_HOURS.")