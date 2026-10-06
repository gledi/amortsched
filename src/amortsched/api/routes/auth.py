from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from amortsched.api.cookies import REFRESH_COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from amortsched.api.dependencies import (
    ApiConfig,
    AuthenticateUser,
    CreateRefreshToken,
    Logout,
    RateLimitGuard,
    RefreshTokens,
    RegisterUser,
    RequestPasswordReset,
    ResetPassword,
    SendVerificationEmail,
    TokenSvc,
    VerifyEmail,
    client_ip,
    per_ip_limit,
)
from amortsched.api.schemas.auth import (
    AuthResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from amortsched.app.commands.accounts import (
    RequestPasswordResetCommand,
    ResetPasswordCommand,
    SendVerificationEmailCommand,
    VerifyEmailCommand,
)
from amortsched.app.commands.users import (
    AuthenticateUserCommand,
    CreateRefreshTokenCommand,
    LogoutCommand,
    RefreshTokensCommand,
    RegisterUserCommand,
)
from amortsched.core.errors import RefreshTokenNotFoundError

router = APIRouter(prefix="/api/auth", tags=["auth"])

type RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(per_ip_limit("register", limit=10, window_seconds=3600))],
)
async def register(
    body: RegisterRequest,
    response: Response,
    handler: RegisterUser,
    token_service: TokenSvc,
    refresh_handler: CreateRefreshToken,
    verification: SendVerificationEmail,
    settings: ApiConfig,
) -> AuthResponse:
    command = RegisterUserCommand(email=body.email, name=body.name, password=body.password)
    user = await handler.handle(command)
    await verification.handle(SendVerificationEmailCommand(user_id=user.id))
    refresh_token = await refresh_handler.handle(CreateRefreshTokenCommand(user_id=user.id))
    set_refresh_cookie(response, refresh_token, settings)
    return AuthResponse(user=UserResponse.from_entity(user), access_token=token_service.create_access_token(user.id))


@router.post("/token", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    handler: AuthenticateUser,
    token_service: TokenSvc,
    refresh_handler: CreateRefreshToken,
    guard: RateLimitGuard,
    settings: ApiConfig,
) -> TokenResponse:
    await guard.check(f"login:ip:{client_ip(request)}", limit=30, window_seconds=300)
    await guard.check(f"login:email:{form_data.username.casefold()}", limit=10, window_seconds=900)
    user = await handler.handle(AuthenticateUserCommand(email=form_data.username, password=form_data.password))
    refresh_token = await refresh_handler.handle(CreateRefreshTokenCommand(user_id=user.id))
    set_refresh_cookie(response, refresh_token, settings)
    return TokenResponse(access_token=token_service.create_access_token(user.id))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    handler: RefreshTokens,
    settings: ApiConfig,
    refresh_token: RefreshCookie = None,
) -> TokenResponse:
    if not refresh_token:
        raise RefreshTokenNotFoundError()
    result = await handler.handle(RefreshTokensCommand(refresh_token=refresh_token))
    set_refresh_cookie(response, result.refresh_token, settings)
    return TokenResponse(access_token=result.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    handler: Logout,
    settings: ApiConfig,
    refresh_token: RefreshCookie = None,
) -> None:
    if refresh_token:
        await handler.handle(LogoutCommand(refresh_token=refresh_token))
    clear_refresh_cookie(response, settings)


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(body: VerifyEmailRequest, handler: VerifyEmail) -> UserResponse:
    user = await handler.handle(VerifyEmailCommand(token=body.token))
    return UserResponse.from_entity(user)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    handler: RequestPasswordReset,
    guard: RateLimitGuard,
) -> None:
    await guard.check(f"password-reset:ip:{client_ip(request)}", limit=10, window_seconds=900)
    await guard.check(f"password-reset:email:{body.email.casefold()}", limit=3, window_seconds=900)
    await handler.handle(RequestPasswordResetCommand(email=body.email))


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(per_ip_limit("password-reset-confirm", limit=20, window_seconds=900))],
)
async def confirm_password_reset(body: PasswordResetConfirmRequest, handler: ResetPassword) -> None:
    await handler.handle(ResetPasswordCommand(token=body.token, password=body.password))
