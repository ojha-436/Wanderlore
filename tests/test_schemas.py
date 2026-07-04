"""Input validation and model round-tripping."""
import pytest
from pydantic import ValidationError

from app.schemas import DiscoverRequest, DiscoverResponse, ItineraryRequest

from .factories import make_core


def test_discover_defaults():
    req = DiscoverRequest(destination="Kyoto")
    assert req.num_days == 3 and req.pace == "balanced" and req.interests == []


def test_discover_rejects_short_destination():
    with pytest.raises(ValidationError):
        DiscoverRequest(destination="")


def test_discover_rejects_bad_num_days():
    with pytest.raises(ValidationError):
        DiscoverRequest(destination="Kyoto", num_days=0)
    with pytest.raises(ValidationError):
        DiscoverRequest(destination="Kyoto", num_days=999)


def test_itinerary_request_validation():
    with pytest.raises(ValidationError):
        ItineraryRequest(items=[], num_days=0, daily_hours=8)
    with pytest.raises(ValidationError):
        ItineraryRequest(items=[], num_days=3, daily_hours=99)


def test_discover_response_roundtrip():
    core = make_core()
    resp = DiscoverResponse(
        destination="Jaipur", summary=core.summary, attractions=core.attractions,
        hidden_gems=core.hidden_gems, experiences=core.experiences, events=[], event_citations=[],
    )
    restored = DiscoverResponse.model_validate(resp.model_dump())
    assert restored.destination == "Jaipur"
    assert len(restored.attractions) == 4
