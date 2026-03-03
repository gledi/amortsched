"""Authentication routes."""

from fastapi import APIRouter, Depends

from amortsched.app.users import (
    AuthenticateUserCommand,
    AuthenticateUserHandler,
    RegisterUserCommand,
    RegisterUserHandler,
)
from amortsched.auth import JoseTokenService
from amortsched.web.deps import get_authenticate_user_handler, get_register_user_handler, get_token_service
from amortsched.web.models import AuthResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(
    payload: RegisterRequest,
    handler: RegisterUserHandler = Depends(get_register_user_handler),  # noqa: B008
    token_service: JoseTokenService = Depends(get_token_service),  # noqa: B008
) -> AuthResponse:
    user = handler.handle(RegisterUserCommand(email=payload.email, name=payload.name, password=payload.password))
    token = token_service.create_access_token(user.id)
    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name, isActive=user.is_active),
        token=token,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    handler: AuthenticateUserHandler = Depends(get_authenticate_user_handler),  # noqa: B008
    token_service: JoseTokenService = Depends(get_token_service),  # noqa: B008
) -> AuthResponse:
    user = handler.handle(AuthenticateUserCommand(email=payload.email, password=payload.password))
    token = token_service.create_access_token(user.id)
    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name, isActive=user.is_active),
        token=token,
    )
