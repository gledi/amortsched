"""User and profile routes."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from amortsched.api.middleware import get_current_user_id
from amortsched.api.validators import ProfileResponse, UpsertProfileRequest, UserResponse
from amortsched.app.users import (
    GetProfileHandler,
    GetProfileQuery,
    GetUserHandler,
    GetUserQuery,
    UpsertProfileCommand,
    UpsertProfileHandler,
)


async def get_me(request: Request) -> Response:
    user_id = get_current_user_id(request)
    container = request.app.state.container
    handler = container.resolve(GetUserHandler)
    user = handler.handle(GetUserQuery(user_id=user_id))
    resp = UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active)
    return Response(content=resp.to_json(), media_type="application/json")


async def get_profile(request: Request) -> Response:
    user_id = get_current_user_id(request)
    container = request.app.state.container
    handler = container.resolve(GetProfileHandler)
    profile = handler.handle(GetProfileQuery(user_id=user_id))
    resp = ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
    return Response(content=resp.to_json(), media_type="application/json")


async def upsert_profile(request: Request) -> Response:
    user_id = get_current_user_id(request)
    body = await request.body()
    req = UpsertProfileRequest.from_json(body)
    container = request.app.state.container
    handler = container.resolve(UpsertProfileHandler)
    profile = handler.handle(
        UpsertProfileCommand(
            user_id=user_id,
            display_name=req.display_name,
            phone=req.phone,
            locale=req.locale,
            timezone=req.timezone,
        )
    )
    resp = ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
    return Response(content=resp.to_json(), media_type="application/json")


routes = [
    Route("/api/users/me", get_me, methods=["GET"]),
    Route("/api/users/me/profile", get_profile, methods=["GET"]),
    Route("/api/users/me/profile", upsert_profile, methods=["PUT"]),
]
