"""Pydantic models.

LLM-output models (used as Gemini `response_schema`) use only required fields and
Literal enums for reliable structured output. Input / app models may use defaults
and Optionals freely.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Pace = Literal["relaxed", "balanced", "packed"]
ExperienceType = Literal["food", "craft", "ritual", "community", "nature", "performance"]

# --------------------------------------------------------------------------- #
# LLM-output models (Gemini response_schema)
# --------------------------------------------------------------------------- #


class Attraction(BaseModel):
    name: str
    category: str = Field(description="e.g. monument, museum, temple, viewpoint, market.")
    why_for_you: str = Field(description="Why this fits the traveler's interests.")
    area: str = Field(description="Neighborhood / district for grouping.")
    best_time: str = Field(description="Best time of day / conditions to visit.")
    suggested_duration_minutes: int = Field(description="Typical visit length in minutes.")
    photo_url: Optional[str] = None
    rating: Optional[float] = None


class HiddenGem(BaseModel):
    name: str
    why_special: str = Field(description="What makes this off-the-beaten-path spot special.")
    area: str
    suggested_duration_minutes: int
    photo_url: Optional[str] = None
    rating: Optional[float] = None


class CulturalExperience(BaseModel):
    name: str
    type: ExperienceType
    description: str
    etiquette_tip: str = Field(description="How to engage respectfully.")
    suggested_duration_minutes: int


class LocalEvent(BaseModel):
    name: str
    category: str = Field(description="e.g. festival, market, performance, exhibition.")
    when_hint: str = Field(description="When it happens relative to the trip dates.")
    description: str
    why_go: str


class DiscoverCore(BaseModel):
    """Structured (non-grounded) part of discovery."""
    summary: str = Field(description="One-paragraph cultural overview of the destination.")
    attractions: List[Attraction]
    hidden_gems: List[HiddenGem]
    experiences: List[CulturalExperience]


class HeritageStory(BaseModel):
    title: str
    story: str = Field(description="Immersive multi-paragraph narrative of history and legend.")
    heritage_note: str = Field(description="Cultural significance and why it matters today.")
    did_you_know: str = Field(description="A surprising fact or legend.")


class LandmarkStory(BaseModel):
    identified: bool = Field(description="True only if a real landmark/place is recognized.")
    name: str = Field(description="Best-guess landmark name, or empty if not identified.")
    confidence: float = Field(description="0.0-1.0 identification confidence.")
    location_guess: str = Field(description="Likely city / country, or empty.")
    title: str
    story: str
    heritage_note: str


# --------------------------------------------------------------------------- #
# Grounding
# --------------------------------------------------------------------------- #


class Citation(BaseModel):
    title: str = ""
    uri: str = ""


class EventsResult(BaseModel):
    events: List[LocalEvent] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Input models
# --------------------------------------------------------------------------- #


class DiscoverRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=120)
    travel_dates: Optional[str] = Field(default=None, max_length=120,
                                        description="e.g. 'March 2026' or '10-14 Mar' (for event grounding).")
    num_days: int = Field(default=3, ge=1, le=30)
    interests: List[str] = Field(default_factory=list, max_length=30)
    pace: Pace = "balanced"
    traveler_notes: str = Field(default="", max_length=1000)


class StoryRequest(BaseModel):
    place: str = Field(min_length=2, max_length=160)
    destination_context: Optional[str] = Field(default=None, max_length=120)
    tone: Literal["historical", "myth", "humorous"] = "historical"


class ItineraryItemInput(BaseModel):
    id: str = Field(max_length=80)
    name: str = Field(max_length=200)
    category: str = Field(default="attraction", max_length=60)
    duration_minutes: int = Field(ge=0, le=1440)


class ItineraryRequest(BaseModel):
    items: List[ItineraryItemInput] = Field(max_length=100)
    num_days: int = Field(ge=1, le=30)
    daily_hours: float = Field(default=8.0, ge=1, le=16)


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=120)
    interests: Optional[List[str]] = None
    travel_style: Optional[str] = Field(default=None, max_length=120)
    home_city: Optional[str] = Field(default=None, max_length=120)


class TripSave(BaseModel):
    destination: str = Field(max_length=120)
    label: Optional[str] = Field(default=None, max_length=120)
    payload: dict = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# App-computed / response models
# --------------------------------------------------------------------------- #


class DiscoverResponse(BaseModel):
    destination: str
    summary: str
    attractions: List[Attraction]
    hidden_gems: List[HiddenGem]
    experiences: List[CulturalExperience]
    events: List[LocalEvent]
    event_citations: List[Citation]
    weather_advisory: Optional[dict] = None
    notes: str = ""


class ItineraryItem(BaseModel):
    id: str
    name: str
    category: str
    duration_minutes: int


class ItineraryDay(BaseModel):
    day_number: int
    items: List[ItineraryItem]
    minutes_used: int


class Itinerary(BaseModel):
    days: List[ItineraryDay]
    overflow: List[ItineraryItem]
    daily_minutes_budget: int
    total_minutes_planned: int


class User(BaseModel):
    """Authenticated identity derived from a verified Firebase ID token."""
    uid: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    provider: Optional[str] = None


class UserProfile(BaseModel):
    uid: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    travel_style: str = ""
    home_city: str = ""
