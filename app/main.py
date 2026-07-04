"""FastAPI application entrypoint.

Serves the JSON API under /api/* and the static frontend at /. Health at /api/healthz.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routes import meta, profile, travel

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="GenAI travel & culture companion: discover, storytelling, heritage, events, itinerary.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers (registered before the static mount so /api/* wins).
app.include_router(meta.router)
app.include_router(profile.router)
app.include_router(travel.router)

# Static frontend at "/" (index.html, login.html, app.html, assets). Mounted last.
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
