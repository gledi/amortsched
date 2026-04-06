from fastapi import APIRouter, Depends, status

from amortsched.adapters.security.jwt import JoseTokenService
from amortsched.api.dependencies import (
    get_authenticate_user_handler,
    get_register_user_handler,
    get_token_service,
)
from amortsched.api.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from amortsched.app.commands.users import (
    AuthenticateUserCommand,
    AuthenticateUserHandler,
    RegisterUserCommand,
    RegisterUserHandler,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    handler: RegisterUserHandler = Depends(get_register_user_handler),
    token_service: JoseTokenService = Depends(get_token_service),
) -> AuthResponse:
    command = RegisterUserCommand(email=body.email, name=body.name, password=body.password)
    user = await handler.handle(command)
    token = token_service.create_access_token(user.id)
    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active),
        token=token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    handler: AuthenticateUserHandler = Depends(get_authenticate_user_handler),
    token_service: JoseTokenService = Depends(get_token_service),
) -> AuthResponse:
    command = AuthenticateUserCommand(email=body.email, password=body.password)
    user = await handler.handle(command)
    token = token_service.create_access_token(user.id)
    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active),
        token=token,
    )
