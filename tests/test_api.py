"""API smoke/integration tests via TestClient with dependency overrides."""
from app.config import Settings, get_settings
from app.deps import get_current_user, get_gemini_client, get_repository
from app.main import app
from app.schemas import User

from .factories import FakeGemini, FakeRepo

EVENTS_JSON = '[{"name":"Teej","category":"festival","when_hint":"soon","description":"d","why_go":"w"}]'


def _override(gemini=None, repo=None):
    app.dependency_overrides[get_current_user] = lambda: User(uid="u1", email="e@x.com", display_name="Ed")
    app.dependency_overrides[get_gemini_client] = lambda: gemini or FakeGemini(grounded_text=EVENTS_JSON)
    app.dependency_overrides[get_repository] = lambda: repo or FakeRepo()


def test_healthz(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_config_public(client):
    r = client.get("/api/config")
    assert r.status_code == 200 and "firebase" in r.json()


def test_discover_returns_all_sections(client):
    _override()
    r = client.post("/api/discover", json={"destination": "Jaipur", "interests": ["history"], "num_days": 3})
    assert r.status_code == 200
    d = r.json()
    assert d["attractions"] and d["hidden_gems"] and d["experiences"]
    assert d["events"][0]["name"] == "Teej"


def test_itinerary_packs(client):
    _override()
    body = {
        "items": [
            {"id": "a", "name": "Fort", "category": "attraction", "duration_minutes": 120},
            {"id": "b", "name": "Museum", "category": "museum", "duration_minutes": 90},
        ],
        "num_days": 1, "daily_hours": 8,
    }
    r = client.post("/api/itinerary", json=body)
    assert r.status_code == 200
    it = r.json()
    assert len(it["days"]) == 1
    assert it["days"][0]["minutes_used"] == 210


def test_story_returns_narrative(client):
    _override()
    r = client.post("/api/story", json={"place": "Amber Fort"})
    assert r.status_code == 200 and r.json()["story"]


def test_protected_route_requires_auth(client):
    app.dependency_overrides[get_settings] = lambda: Settings(auth_required=True)
    r = client.post("/api/discover", json={"destination": "Jaipur"})
    assert r.status_code == 401
