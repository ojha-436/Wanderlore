"""Storytelling (text + multimodal photo) with a fake Gemini client."""
from app.story import story_from_photo, tell_story

from .factories import FakeGemini, make_landmark


def test_tell_story_returns_heritage_story():
    fake = FakeGemini()
    story = tell_story(fake, "Amber Fort", destination_context="Jaipur")
    assert story.title and story.story and story.heritage_note
    # place is embedded as delimited untrusted data
    assert "<<<PLACE" in fake.last_contents[0]


def test_photo_story_attaches_image_part():
    fake = FakeGemini()
    result = story_from_photo(fake, b"\xff\xd8\xff\xe0", "image/jpeg")
    assert result.identified is True
    assert len(fake.last_contents) == 2
    assert fake.last_contents[1]["__image__"] == 4
    assert fake.last_contents[1]["mime"] == "image/jpeg"


def test_photo_story_reports_unidentified_landmark():
    fake = FakeGemini(landmark=make_landmark(identified=False))
    result = story_from_photo(fake, b"\x89PNG", "image/png")
    assert result.identified is False
    assert result.name == ""
