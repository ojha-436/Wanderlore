"""Public metadata routes (no auth): health + Firebase web config."""
from fastapi import APIRouter, Depends

from ..config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/healthz")
def health(settings: Settings = Depends(get_settings)) -> dict:
    """Health check under /api (Google's frontend reserves the bare /healthz path)."""
    return {"status": "ok", "app": settings.app_name}


@router.get("/config")
def firebase_config(settings: Settings = Depends(get_settings)) -> dict:
    """Non-secret Firebase web config used by the browser to init Auth."""
    return {
        "firebase": settings.firebase_web_config(),
        "appName": settings.app_name,
        "authRequired": settings.auth_required,
    }
