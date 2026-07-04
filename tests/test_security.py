"""Auth dependency: token verification (Email/Password + Google) and dev bypass."""
import pytest
from fastapi import HTTPException

from app.config import Settings
from app.deps import get_current_user


def _settings(auth_required=True):
    return Settings(auth_required=auth_required)


def test_missing_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None, settings=_settings(True))
    assert exc.value.status_code == 401


def test_wrong_scheme_raises_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Token abc", settings=_settings(True))
    assert exc.value.status_code == 401


def test_valid_google_token_returns_user(monkeypatch):
    monkeypatch.setattr(
        "app.deps.verify_firebase_token",
        lambda t: {"uid": "u1", "email": "a@b.com", "name": "Ann", "picture": "http://p/a.png",
                   "firebase": {"sign_in_provider": "google.com"}},
    )
    user = get_current_user(authorization="Bearer good", settings=_settings(True))
    assert user.uid == "u1"
    assert user.email == "a@b.com"
    assert user.provider == "google.com"


def test_invalid_token_raises_401(monkeypatch):
    def boom(_):
        raise ValueError("bad token")
    monkeypatch.setattr("app.deps.verify_firebase_token", boom)
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Bearer bad", settings=_settings(True))
    assert exc.value.status_code == 401


def test_auth_disabled_returns_demo_user():
    user = get_current_user(authorization=None, settings=_settings(False))
    assert user.uid == "demo-user"
