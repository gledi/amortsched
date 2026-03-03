"""User and profile routes."""

import uuid

from fastapi import APIRouter, Depends

from amortsched.app.users import (
    GetProfileHandler,
    GetProfileQuery,
    GetUserHandler,
    GetUserQuery,
    UpsertProfileCommand,
    UpsertProfileHandler,
)
from amortsched.web.deps import get_profile_handler, get_upsert_profile_handler, get_user_handler
from amortsched.web.middleware import get_current_user_id
from amortsched.web.models import ProfileResponse, UpsertProfileRequest, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: GetUserHandler = Depends(get_user_handler),  # noqa: B008
) -> UserResponse:
    user = handler.handle(GetUserQuery(user_id=user_id))
    return UserResponse(id=user.id, email=user.email, name=user.name, isActive=user.is_active)


@router.get("/me/profile", response_model=ProfileResponse)
def get_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: GetProfileHandler = Depends(get_profile_handler),  # noqa: B008
) -> ProfileResponse:
    profile = handler.handle(GetProfileQuery(user_id=user_id))
    return ProfileResponse(
        id=profile.id,
        userId=profile.user_id,
        displayName=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        createdAt=profile.created_at,
        updatedAt=profile.updated_at,
    )


@router.put("/me/profile", response_model=ProfileResponse)
def upsert_profile(
    payload: UpsertProfileRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),  # noqa: B008
    handler: UpsertProfileHandler = Depends(get_upsert_profile_handler),  # noqa: B008
) -> ProfileResponse:
    profile = handler.handle(
        UpsertProfileCommand(
            user_id=user_id,
            display_name=payload.display_name,
            phone=payload.phone,
            locale=payload.locale,
            timezone=payload.timezone,
        )
    )
    return ProfileResponse(
        id=profile.id,
        userId=profile.user_id,
        displayName=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        createdAt=profile.created_at,
        updatedAt=profile.updated_at,
    )
