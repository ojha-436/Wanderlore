"""Test builders and in-memory fakes (no cloud dependencies)."""
from typing import List, Optional

from app.schemas import (
    Attraction,
    CulturalExperience,
    DiscoverCore,
    HeritageStory,
    HiddenGem,
    ItineraryItemInput,
    LandmarkStory,
)


def make_attraction(name="Amber Fort", dur=120) -> Attraction:
    return Attraction(
        name=name, category="fort", why_for_you="Matches your love of history.",
        area="Old City", best_time="early morning", suggested_duration_minutes=dur,
    )


def make_gem(name="Panna Meena Stepwell", dur=45) -> HiddenGem:
    return HiddenGem(name=name, why_special="Quiet, geometric, barely touristed.",
                     area="Amer", suggested_duration_minutes=dur)


def make_experience(name="Block-printing workshop", dur=90) -> CulturalExperience:
    return CulturalExperience(name=name, type="craft", description="Learn traditional printing.",
                              etiquette_tip="Ask before photographing artisans.", suggested_duration_minutes=dur)


def make_core() -> DiscoverCore:
    return DiscoverCore(
        summary="A rose-hued city of forts, bazaars and living craft.",
        attractions=[make_attraction("Amber Fort", 120), make_attraction("City Palace", 90),
                     make_attraction("Hawa Mahal", 45), make_attraction("Jantar Mantar", 60)],
        hidden_gems=[make_gem("Panna Meena Stepwell", 45), make_gem("Anokhi Museum", 60),
                     make_gem("Gaitore Cenotaphs", 40)],
        experiences=[make_experience("Block-printing workshop", 90),
                     make_experience("Thali dinner", 75), make_experience("Bazaar walk", 60)],
    )


def make_story() -> HeritageStory:
    return HeritageStory(title="The Fort of Mirrors",
                         story="Long ago...\n\nThe walls still whisper.",
                         heritage_note="A UNESCO-listed symbol of Rajput craft.",
                         did_you_know="Its mirror hall lights from a single candle.")


def make_landmark(identified=True) -> LandmarkStory:
    return LandmarkStory(identified=identified, name="Amber Fort" if identified else "",
                         confidence=0.9 if identified else 0.1,
                         location_guess="Jaipur, India" if identified else "",
                         title="The Fort of Mirrors", story="Perched on the hill...",
                         heritage_note="Rajput-Mughal architecture.")


def items(*durations) -> List[ItineraryItemInput]:
    return [ItineraryItemInput(id=f"i{i}", name=f"Place {i}", category="attraction", duration_minutes=d)
            for i, d in enumerate(durations)]


class FakeGemini:
    def __init__(self, core=None, story=None, landmark=None, grounded_text="[]", citations=None,
                 grounded_raises=False):
        self.core = core; self.story = story; self.landmark = landmark
        self.grounded_text = grounded_text; self.citations = citations or []
        self.grounded_raises = grounded_raises
        self.calls = 0; self.last_contents = None; self.last_system = None

    def image_part(self, data: bytes, mime_type: str):
        return {"__image__": len(data), "mime": mime_type}

    def generate_structured(self, *, system_instruction, contents, response_schema, temperature=0.6):
        self.calls += 1; self.last_contents = contents; self.last_system = system_instruction
        if response_schema is DiscoverCore:
            return self.core or make_core()
        if response_schema is HeritageStory:
            return self.story or make_story()
        if response_schema is LandmarkStory:
            return self.landmark or make_landmark()
        raise AssertionError(f"Unexpected schema {response_schema}")

    def generate_grounded(self, *, system_instruction, contents, temperature=0.4):
        if self.grounded_raises:
            raise RuntimeError("grounding unavailable")
        return {"text": self.grounded_text, "citations": self.citations}

    def generate_text(self, *, system_instruction, contents, temperature=0.8):
        return "some text"


class FakeRepo:
    def __init__(self):
        self.profiles = {}; self.trips = {}

    def get_profile(self, uid): return self.profiles.get(uid)
    def upsert_profile(self, profile): self.profiles[profile.uid] = profile.model_dump()
    def save_trip(self, uid, destination, label, payload):
        self.trips.setdefault(uid, []).append({"destination": destination, "label": label, "payload": payload})
        return "trip-id"
    def list_trips(self, uid, limit=20): return self.trips.get(uid, [])
