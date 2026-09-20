"""Run the FastAPI app locally with PostgreSQL + real FlightAPI.io data.

Uses the local PostgreSQL database (from backend/.env DATABASE_URL),
FlightAPI.io for real airfare prices, and direct DB writes
(no Kafka/Redis required).
"""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

# Load backend/.env first, then root .env as fallback (no override)
load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")

# Set environment for the child uvicorn process
env = os.environ.copy()
env["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY", "local-development-secret-key-for-testing-only-12345"
)

# Real FlightAPI.io data — key must be set in .env
flightapi_key = os.getenv("FLIGHTAPI_API_KEY", "").strip()
if not flightapi_key:
    raise SystemExit(
        "FLIGHTAPI_API_KEY is not set. Add it to .env or backend/.env."
    )
env["FLIGHTAPI_API_KEY"] = flightapi_key
env["FLIGHTAPI_STORE_MODE"] = os.getenv("FLIGHTAPI_STORE_MODE", "direct")
env["COLLECTION_INTERVAL_HOURS"] = os.getenv("COLLECTION_INTERVAL_HOURS", "3")

if not env.get("DATABASE_URL"):
    raise SystemExit(
        "DATABASE_URL is not set. Add it to backend/.env, e.g.\n"
        "DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/airfare_db"
    )

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload",
    ]
    subprocess.run(cmd, cwd=base_dir, env=env)
