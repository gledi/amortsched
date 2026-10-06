import uuid

from fastapi import APIRouter, HTTPException, Response, status

from amortsched.api.cookies import clear_refresh_cookie, set_refresh_cookie
from amortsched.api.dependencies import (
    ApiConfig,
    ChangePassword,
    CreateRefreshToken,
    CurrentUserId,
    DeleteAccount,
    ExportAccountData,
    GetProfile,
    GetUser,
    RateLimitGuard,
    RevokeAllSessions,
    SendVerificationEmail,
    TokenSvc,
    UpdateAccount,
    UpsertProfile,
)
from amortsched.api.schemas.auth import TokenResponse, UserResponse
from amortsched.api.schemas.users import (
    AccountExportResponse,
    ChangePasswordRequest,
    DeleteAccountRequest,
    ProfileResponse,
    UpdateAccountRequest,
    UpsertProfileRequest,
)
from amortsched.app.commands.accounts import (
    ChangePasswordCommand,
    DeleteAccountCommand,
    RevokeAllSessionsCommand,
    SendVerificationEmailCommand,
    UpdateAccountCommand,
)
from amortsched.app.commands.users import CreateRefreshTokenCommand, UpsertProfileCommand
from amortsched.app.queries.users import ExportAccountDataQuery, GetProfileQuery, GetUserQuery
from amortsched.core.utils import now

router = APIRouter(prefix="/api/users", tags=["users"])


async def _start_fresh_session(
    user_id: uuid.UUID,
    response: Response,
    token_service: TokenSvc,
    refresh_handler: CreateRefreshToken,
    settings: ApiConfig,
) -> TokenResponse:
    refresh_token = await refresh_handler.handle(CreateRefreshTokenCommand(user_id=user_id))
    set_refresh_cookie(response, refresh_token, settings)
    return TokenResponse(access_token=token_service.create_access_token(user_id))


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user_id: CurrentUserId, handler: GetUser) -> UserResponse:
    user = await handler.handle(GetUserQuery(user_id=current_user_id))
    return UserResponse.from_entity(user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    body: UpdateAccountRequest,
    current_user_id: CurrentUserId,
    handler: UpdateAccount,
) -> UserResponse:
    user = await handler.handle(UpdateAccountCommand(user_id=current_user_id, name=body.name))
    return UserResponse.from_entity(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    body: DeleteAccountRequest,
    response: Response,
    current_user_id: CurrentUserId,
    handler: DeleteAccount,
    settings: ApiConfig,
) -> None:
    await handler.handle(DeleteAccountCommand(user_id=current_user_id, password=body.password))
    clear_refresh_cookie(response, settings)


@router.post("/me/verification-email", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification_email(
    current_user_id: CurrentUserId,
    handler: SendVerificationEmail,
    guard: RateLimitGuard,
) -> None:
    await guard.check(f"verification-email:user:{current_user_id}", limit=3, window_seconds=900)
    await handler.handle(SendVerificationEmailCommand(user_id=current_user_id))


@router.post("/me/password", response_model=TokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    current_user_id: CurrentUserId,
    handler: ChangePassword,
    token_service: TokenSvc,
    refresh_handler: CreateRefreshToken,
    guard: RateLimitGuard,
    settings: ApiConfig,
) -> TokenResponse:
    await guard.check(f"change-password:user:{current_user_id}", limit=10, window_seconds=900)
    command = ChangePasswordCommand(
        user_id=current_user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    _ = await handler.handle(command)
    return await _start_fresh_session(current_user_id, response, token_service, refresh_handler, settings)


@router.post("/me/sessions/revoke", response_model=TokenResponse)
async def revoke_all_sessions(
    response: Response,
    current_user_id: CurrentUserId,
    handler: RevokeAllSessions,
    token_service: TokenSvc,
    refresh_handler: CreateRefreshToken,
    settings: ApiConfig,
) -> TokenResponse:
    await handler.handle(RevokeAllSessionsCommand(user_id=current_user_id))
    return await _start_fresh_session(current_user_id, response, token_service, refresh_handler, settings)


@router.get("/me/export", response_model=AccountExportResponse)
async def export_account_data(
    response: Response,
    current_user_id: CurrentUserId,
    handler: ExportAccountData,
) -> AccountExportResponse:
    result = await handler.handle(ExportAccountDataQuery(user_id=current_user_id))
    exported_at = now()
    filename = f"amortsched-export-{exported_at:%Y%m%d}.json"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return AccountExportResponse.from_result(result, exported_at)


@router.get("/me/profile", response_model=ProfileResponse)
async def get_current_user_profile(
    current_user_id: CurrentUserId,
    handler: GetProfile,
) -> ProfileResponse:
    profile = await handler.handle(GetProfileQuery(user_id=current_user_id))
    return ProfileResponse.from_entity(profile)


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
        currency=body.currency,
    )
    profile = await handler.handle(command)
    return ProfileResponse.from_entity(profile)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, handler: GetUser, _current_user_id: CurrentUserId) -> UserResponse:
    if user_id != _current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user")
    user = await handler.handle(GetUserQuery(user_id=user_id))
    return UserResponse.from_entity(user)


@router.get("/{user_id}/profile", response_model=ProfileResponse)
async def get_profile(
    user_id: uuid.UUID,
    handler: GetProfile,
    _current_user_id: CurrentUserId,
) -> ProfileResponse:
    if user_id != _current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user")
    profile = await handler.handle(GetProfileQuery(user_id=user_id))
    return ProfileResponse.from_entity(profile)


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
        currency=body.currency,
    )
    profile = await handler.handle(command)
    return ProfileResponse.from_entity(profile)
