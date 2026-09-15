import uuid

from fastapi import APIRouter, HTTPException, status

from amortsched.api.dependencies import CurrentUserId, GetProfile, GetUser, UpsertProfile
from amortsched.api.schemas.auth import UserResponse
from amortsched.api.schemas.users import ProfileResponse, UpsertProfileRequest
from amortsched.app.commands.users import UpsertProfileCommand
from amortsched.app.queries.users import GetProfileQuery, GetUserQuery

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user_id: CurrentUserId, handler: GetUser) -> UserResponse:
    user = await handler.handle(GetUserQuery(user_id=current_user_id))
    return UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active)


@router.get("/me/profile", response_model=ProfileResponse)
async def get_current_user_profile(
    current_user_id: CurrentUserId,
    handler: GetProfile,
) -> ProfileResponse:
    profile = await handler.handle(GetProfileQuery(user_id=current_user_id))
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put("/me/profile", response_model=ProfileResponse)
async def upsert_current_user_profile(
    body: UpsertProfileRequest,
    current_user_id: CurrentUserId,
    handler: UpsertProfile,
) -> ProfileResponse:
    command = UpsertProfileCommand(
        user_id=current_user_id,
        display_name=body.display_name,
        phone=body.phone,
        locale=body.locale,
        timezone=body.timezone,
    )
    profile = await handler.handle(command)
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, handler: GetUser, _current_user_id: CurrentUserId) -> UserResponse:
    if user_id != _current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user")
    user = await handler.handle(GetUserQuery(user_id=user_id))
    return UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active)


@router.get("/{user_id}/profile", response_model=ProfileResponse)
async def get_profile(
    user_id: uuid.UUID,
    handler: GetProfile,
    _current_user_id: CurrentUserId,
) -> ProfileResponse:
    if user_id != _current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user")
    profile = await handler.handle(GetProfileQuery(user_id=user_id))
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put("/{user_id}/profile", response_model=ProfileResponse)
async def upsert_profile(
    user_id: uuid.UUID,
    body: UpsertProfileRequest,
    handler: UpsertProfile,
    _current_user_id: CurrentUserId,
) -> ProfileResponse:
    if user_id != _current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify another user")
    command = UpsertProfileCommand(
        user_id=user_id,
        display_name=body.display_name,
        phone=body.phone,
        locale=body.locale,
        timezone=body.timezone,
    )
    profile = await handler.handle(command)
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
