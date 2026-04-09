from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from amortsched.api.dependencies import (
    AuthenticateUser,
    CreateRefreshToken,
    Logout,
    RefreshTokens,
    RegisterUser,
    TokenSvc,
)
from amortsched.api.schemas.auth import (
    AuthResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from amortsched.app.commands.users import (
    AuthenticateUserCommand,
    CreateRefreshTokenCommand,
    LogoutCommand,
    RefreshTokensCommand,
    RegisterUserCommand,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    handler: RegisterUser,
    token_service: TokenSvc,
    refresh_handler: CreateRefreshToken,
) -> AuthResponse:
    command = RegisterUserCommand(email=body.email, name=body.name, password=body.password)
    user = await handler.handle(command)
    access_token = token_service.create_access_token(user.id)
    refresh_token = await refresh_handler.handle(CreateRefreshTokenCommand(user_id=user.id))
    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/token", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    handler: AuthenticateUser,
    token_service: TokenSvc,
    refresh_handler: CreateRefreshToken,
) -> TokenResponse:
    command = AuthenticateUserCommand(email=form_data.username, password=form_data.password)
    user = await handler.handle(command)
    access_token = token_service.create_access_token(user.id)
    refresh_token = await refresh_handler.handle(CreateRefreshTokenCommand(user_id=user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshTokenRequest,
    handler: RefreshTokens,
) -> TokenResponse:
    result = await handler.handle(RefreshTokensCommand(refresh_token=body.refresh_token))
    return TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshTokenRequest,
    handler: Logout,
) -> None:
    await handler.handle(LogoutCommand(refresh_token=body.refresh_token))
