"""Profile routes — read/update the signed-in user's profile & interests."""
from fastapi import APIRouter, Depends

from ..deps import get_current_user, get_repository
from ..repository import Repository
from ..schemas import ProfileUpdate, User, UserProfile

router = APIRouter(prefix="/api", tags=["profile"])


def _profile_from(user: User, data: dict) -> UserProfile:
    data = data or {}
    return UserProfile(
        uid=user.uid,
        email=user.email or data.get("email"),
        display_name=data.get("display_name") or user.display_name,
        photo_url=user.photo_url or data.get("photo_url"),
        interests=data.get("interests", []),
        travel_style=data.get("travel_style", ""),
        home_city=data.get("home_city", ""),
    )


@router.get("/me", response_model=UserProfile)
def get_me(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> UserProfile:
    data = repo.get_profile(user.uid)
    profile = _profile_from(user, data or {})
    if not data:  # first login → bootstrap
        repo.upsert_profile(profile)
    return profile


@router.put("/me", response_model=UserProfile)
def update_me(
    update: ProfileUpdate,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> UserProfile:
    profile = _profile_from(user, repo.get_profile(user.uid) or {})
    for key, value in update.model_dump(exclude_none=True).items():
        setattr(profile, key, value)
    repo.upsert_profile(profile)
    return profile
