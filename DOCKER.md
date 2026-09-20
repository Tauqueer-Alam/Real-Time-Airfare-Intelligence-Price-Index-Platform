# Docker Setup

This setup runs the Real-Time Airfare Intelligence Platform in Docker.

## Default stack (recommended)

The default deployment starts **FastAPI + PostgreSQL**. The app runs in
`direct` store mode: the FlightAPI.io collector writes price snapshots straight to
PostgreSQL (no Kafka/Redis required).

```powershell
docker compose up -d --build
```

The API and dashboard will be available at:

```text
http://127.0.0.1:8010
http://127.0.0.1:8010/docs
```

## Deploy on Render with Aiven PostgreSQL

This repository includes `render.yaml` for a Docker web service. Create the
service from the Blueprint, then set these environment variables in Render:

- `DATABASE_URL`: the Aiven PostgreSQL connection string. Keep Aiven's
  `sslmode=require` query parameter in the URL.
- `FLIGHTAPI_API_KEY`: your FlightAPI.io key, or leave it empty when using only
  the generated demo data.
- `JWT_SECRET_KEY`: a long random value if you do not use the generated value.

Render runs `python -m app.startup`. That command creates the schema and
generates demo airports, routes, flights, mock snapshots, and synthetic history
before the API process starts. The seed is idempotent, so restarts do not create
duplicate synthetic history.

If you change `FASTAPI_PORT` in `.env`, use that port instead.

## Generate demo history

The Docker startup command generates the bundled demo routes, flights, mock
snapshots, and 30 days of synthetic history before FastAPI starts. The operation
is idempotent, so it is safe when Render restarts the service.

To generate additional history manually, run the explicit command from the
backend directory:

```powershell
python -m app.scripts.generate_historical_data --days 30 --snapshots-per-day 4
```

To generate one existing route only:

```powershell
python -m app.scripts.generate_historical_data --route DEL-BLR
```

The command writes only `source="synthetic"` snapshots for completed prior
days. It is idempotent, does not alter existing API snapshots, and does not
create synthetic data for Duffel Airways or airline code `ZZ`.

## Full stack (optional Kafka + Redis)

To run the Kafka-based pipeline (Kafka broker, Redis, and the price
consumer that drains Kafka events into PostgreSQL), enable the `full`
profile:

```powershell
docker compose --profile full up -d --build
```

Then set `FLIGHTAPI_STORE_MODE=kafka` in `.env` so the collector produces
events to Kafka instead of writing directly.

## 1. Create environment file

Copy the example file and replace the placeholder secrets before starting:

```powershell
copy .env.example .env
```

Set a strong `POSTGRES_PASSWORD` and a random `JWT_SECRET_KEY` with at least
32 characters. Add your FlightAPI.io API key to `FLIGHTAPI_API_KEY`.
Do not commit the real `.env` file.

## 2. Host ports

Native services on your machine may already occupy the default ports, so the
`.env` file controls the host-side mappings:

- `FASTAPI_PORT=8010` → container port 8000
- `POSTGRES_PORT=5433` → container port 5432 (native PostgreSQL often uses 5432)
- `REDIS_PORT=6380` → container port 6379 (full profile)
- `KAFKA_PORT=9093` → container port 9092 (full profile)

Container-to-container traffic always uses the internal ports
(`postgres:5432`, `redis:6379`, `kafka:9092`).

## 3. Stop the system

Stop containers but keep database/cache/Kafka volumes:

```powershell
docker compose down
```

Stop containers and delete stored Docker volumes:

```powershell
docker compose down -v
```

Use `down -v` only when you intentionally want to remove PostgreSQL, Redis,
and Kafka persisted data.

## Services

- `fastapi`: Runs the FastAPI backend and serves the frontend dashboard.
  Connects to PostgreSQL through `postgres:5432` and stores collected price
  snapshots directly (direct mode).
- `postgres`: Stores flights, price history, and users. Data is persisted in
  the `postgres_data` Docker volume.
- `price-consumer` (full profile): Reads airfare price events from Kafka and
  stores valid records in PostgreSQL.
- `kafka` (full profile): Official `apache/kafka` image in KRaft mode;
  carries price events from the collector to the price consumer.
- `redis` (full profile): Cache for flight search results. PostgreSQL
  remains the source of truth.
