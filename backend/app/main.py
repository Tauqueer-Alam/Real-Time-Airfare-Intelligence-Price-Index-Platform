import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models.airport import Airport
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route
from app.models.user import User
from app.routes.airports import router as airports_router
from app.routes.analytics import router as analytics_router
from app.routes.auth import router as auth_router
from app.routes.flight_routes import router as flight_routes_router
from app.routes.flights import router as flight_router
from app.routes.search import router as search_router
from app.services.collection_scheduler import run_scheduled_collection


class NoCacheStaticFiles(StaticFiles):
    """Serve static files with no-store so browser always fetches fresh assets."""

    def file_response(self, *args, **kwargs):  # noqa: ANN002, ANN003
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    collection_task = asyncio.create_task(run_scheduled_collection(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await collection_task


app = FastAPI(
    title="Real-Time Airfare Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(airports_router)
app.include_router(flight_routes_router)
app.include_router(flight_router)
app.include_router(search_router)
app.include_router(analytics_router)
app.include_router(auth_router)

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/assets", NoCacheStaticFiles(directory=frontend_dir), name="frontend-assets")


@app.get("/")
def home():
    response = FileResponse(frontend_dir / "index.html")
    response.headers["Cache-Control"] = "no-store"
    return response
