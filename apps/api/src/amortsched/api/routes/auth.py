"""Authentication routes."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from amortsched.api.validators import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from amortsched.app.users import (
    AuthenticateUserCommand,
    AuthenticateUserHandler,
    RegisterUserCommand,
    RegisterUserHandler,
)
from amortsched.auth import JoseTokenService


async def register(request: Request) -> Response:
    body = await request.body()
    req = RegisterRequest.from_json(body)
    container = request.app.state.container
    handler = container.resolve(RegisterUserHandler)
    token_service = container.resolve(JoseTokenService)
    user = handler.handle(RegisterUserCommand(email=req.email, name=req.name, password=req.password))
    token = token_service.create_access_token(user.id)
    resp = AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active),
        token=token,
    )
    return Response(content=resp.to_json(), media_type="application/json", status_code=201)


async def login(request: Request) -> Response:
    body = await request.body()
    req = LoginRequest.from_json(body)
    container = request.app.state.container
    handler = container.resolve(AuthenticateUserHandler)
    token_service = container.resolve(JoseTokenService)
    user = handler.handle(AuthenticateUserCommand(email=req.email, password=req.password))
    token = token_service.create_access_token(user.id)
    resp = AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active),
        token=token,
    )
    return Response(content=resp.to_json(), media_type="application/json")


routes = [
    Route("/api/auth/register", register, methods=["POST"]),
    Route("/api/auth/login", login, methods=["POST"]),
]
