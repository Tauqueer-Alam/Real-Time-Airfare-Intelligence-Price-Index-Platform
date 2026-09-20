# Real-Time Airfare Intelligence Platform

A FastAPI dashboard and API for exploring real-time airfare prices, route
analytics, price history, and fare indexes.

## Features

- FastAPI backend with PostgreSQL support
- Searchable airport, route, flight, and price APIs
- Synthetic historical fare data for demos
- FlightAPI.io collection with direct PostgreSQL storage
- Optional Kafka and Redis services for the full local stack
- Frontend dashboard served by FastAPI

## Deploy on Render with Aiven

The repository includes `render.yaml` and a Docker deployment configuration.

1. Create an Aiven PostgreSQL service.
2. Copy its complete Service URI.
3. Create a Render Blueprint from this repository.
4. Set these Render environment variables:

```text
DATABASE_URL=<complete Aiven Service URI including sslmode=require>
FLIGHTAPI_API_KEY=<optional FlightAPI.io key>
JWT_SECRET_KEY=<long random secret>
```

Render runs `python -m app.startup` before starting FastAPI. This creates the
database tables and generates the bundled airports, routes, flights, mock price
snapshots, and synthetic history automatically. The operation is idempotent and
safe across service restarts.

The Render Blueprint limits the deployment demo to 250 routes so the service
becomes usable quickly. Remove `DEMO_ROUTE_LIMIT` for the complete airport route
graph.

The deployed service exposes:

```text
/
/docs
/api/airports
/api/routes
/api/flights
/api/search
/api/analytics
```

## Run locally with Docker

Copy the example environment file and provide a strong database password and
JWT secret:

```powershell
copy .env.example .env
docker compose up -d --build
```

Open the dashboard at `http://127.0.0.1:8010` and API documentation at
`http://127.0.0.1:8010/docs`.

The default Docker stack runs FastAPI and PostgreSQL. To also run Kafka and
Redis:

```powershell
docker compose --profile full up -d --build
```

## Run the backend locally

Use a virtual environment, install the backend dependencies, set
`backend/.env`, and run:

```powershell
cd backend
pip install -r requirements.txt
python -m app.startup
```

For local development with the real FlightAPI.io collector, use
`python run_local.py` after setting `FLIGHTAPI_API_KEY`.

## Generate additional history

Synthetic history is generated automatically during deployment. To generate it
manually for an existing database:

```powershell
cd backend
python -m app.scripts.generate_historical_data --days 30 --snapshots-per-day 4
```

For one route only:

```powershell
python -m app.scripts.generate_historical_data --route DEL-BLR
```

## Tests

Run the backend tests from the project root:

```powershell
cd backend
pytest
```

## Security

Never commit `.env` files or database credentials. If a database URI has been
shared publicly, rotate the database password and update Render's
`DATABASE_URL` value.
