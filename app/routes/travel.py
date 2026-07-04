"""Core travel routes: discover, storytelling (text + photo), itinerary, trips."""
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from ..config import Settings, get_settings
from ..deps import get_current_user, get_gemini_client, get_repository
from ..discover import discover
from ..gemini_client import GeminiClient
from ..itinerary import pack_itinerary
from ..repository import Repository
from ..schemas import (
    DiscoverRequest,
    DiscoverResponse,
    HeritageStory,
    Itinerary,
    ItineraryRequest,
    LandmarkStory,
    StoryRequest,
    TripSave,
    User,
)
from ..story import story_from_photo, tell_story

router = APIRouter(prefix="/api", tags=["travel"])
logger = logging.getLogger(__name__)


@router.post("/discover", response_model=DiscoverResponse)
def discover_route(
    req: DiscoverRequest,
    user: User = Depends(get_current_user),
    client: GeminiClient = Depends(get_gemini_client),
) -> DiscoverResponse:
    return discover(client, req)


@router.post("/story", response_model=HeritageStory)
def story_route(
    req: StoryRequest,
    user: User = Depends(get_current_user),
    client: GeminiClient = Depends(get_gemini_client),
) -> HeritageStory:
    return tell_story(client, req.place, req.destination_context, req.tone)


@router.post("/story/photo", response_model=LandmarkStory)
async def story_photo_route(
    image: UploadFile = File(...),
    caption: Optional[str] = Form(default=None),
    tone: str = Form(default="historical"),
    user: User = Depends(get_current_user),
    client: GeminiClient = Depends(get_gemini_client),
    settings: Settings = Depends(get_settings),
) -> LandmarkStory:
    if image.content_type not in settings.allowed_image_types_list:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {image.content_type}",
        )
    data = await image.read()
    if len(data) > settings.max_image_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the size limit.",
        )
    return story_from_photo(client, data, image.content_type, caption, tone)


@router.post("/itinerary", response_model=Itinerary)
def itinerary_route(
    req: ItineraryRequest,
    user: User = Depends(get_current_user),
) -> Itinerary:
    # Pure, deterministic — no LLM. daily_hours → minutes.
    return pack_itinerary(req.items, req.num_days, int(req.daily_hours * 60))


@router.get("/trips")
def list_trips(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> dict:
    return {"trips": repo.list_trips(user.uid)}


@router.post("/trips")
def save_trip(
    body: TripSave,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> dict:
    try:
        trip_id = repo.save_trip(user.uid, body.destination, body.label or "", body.payload)
    except Exception:  # noqa: BLE001 — persistence best-effort
        logger.exception("Failed to save trip for uid=%s", user.uid)
        raise HTTPException(status_code=500, detail="Could not save trip.")
    return {"id": trip_id}
