import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated

import structlog
from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from amortsched.adapters.email.console import ConsoleEmailSender
from amortsched.adapters.email.smtp import SmtpEmailSender
from amortsched.adapters.persistence.repositories import (
    AsyncSqlAlchemyAccountTokenRepository,
    AsyncSqlAlchemyPlanRepository,
    AsyncSqlAlchemyProfileRepository,
    AsyncSqlAlchemyRefreshTokenRepository,
    AsyncSqlAlchemyScheduleRepository,
    AsyncSqlAlchemyUserRepository,
)
from amortsched.adapters.ratelimit.memory import InMemoryRateLimiter
from amortsched.adapters.ratelimit.redis import RedisRateLimiter
from amortsched.adapters.security.hashers import PBKDF2PasswordHasher
from amortsched.adapters.security.tokens import JwtTokenService
from amortsched.api.config import Settings as ApiSettings
from amortsched.api.config import get_settings
from amortsched.app.commands.accounts import (
    ChangePasswordHandler,
    DeleteAccountHandler,
    RequestPasswordResetHandler,
    ResetPasswordHandler,
    RevokeAllSessionsHandler,
    SendVerificationEmailHandler,
    UpdateAccountHandler,
    VerifyEmailHandler,
)
from amortsched.app.commands.plans import (
    AddInterestRateChangeHandler,
    AddOneTimeExtraPaymentHandler,
    AddRecurringExtraPaymentHandler,
    CreatePlanHandler,
    DeletePlanHandler,
    DeleteScheduleHandler,
    DuplicatePlanHandler,
    ReplaceAdjustmentsHandler,
    SavePlanHandler,
    SaveScheduleHandler,
    UpdatePlanHandler,
)
from amortsched.app.commands.users import (
    AuthenticateUserHandler,
    CreateRefreshTokenHandler,
    LogoutHandler,
    RefreshTokensHandler,
    RegisterUserHandler,
    UpsertProfileHandler,
)
from amortsched.app.ports import EmailMessage, EmailSender, RateLimiter, Settings
from amortsched.app.queries.comparisons import ComparePlansHandler
from amortsched.app.queries.plans import GetPlanHandler, ListPlansHandler
from amortsched.app.queries.schedules import GenerateScheduleHandler, GetScheduleHandler, ListSchedulesHandler
from amortsched.app.queries.tools import PrepayVsInvestPlanHandler, RefinancePlanHandler
from amortsched.app.queries.users import ExportAccountDataHandler, GetProfileHandler, GetUserHandler
from amortsched.core.errors import (
    ExpiredTokenError,
    InvalidTokenError,
    RateLimitExceededError,
    RefreshTokenReplayError,
)

logger = structlog.get_logger()  # pyright: ignore[reportAny]


def get_password_hasher() -> PBKDF2PasswordHasher:
    return PBKDF2PasswordHasher()


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.async_session_factory() as session:  # pyright: ignore[reportAny]
        try:
            yield session
        except RefreshTokenReplayError:
            # Reuse detection revokes the complete refresh-token family. Preserve
            # that security write while still returning the authentication error.
            await session.commit()  # pyright: ignore[reportAny]
            raise
        except BaseException:
            await session.rollback()  # pyright: ignore[reportAny]
            raise
        else:
            await session.commit()  # pyright: ignore[reportAny]


# Function scope commits before the response is sent, so clients never read ahead of their own writes.
type DbSession = Annotated[AsyncSession, Depends(get_session, scope="function")]
type AppSettings = Annotated[Settings, Depends(get_settings)]
type ApiConfig = Annotated[ApiSettings, Depends(get_settings)]
type PasswordHash = Annotated[PBKDF2PasswordHasher, Depends(get_password_hasher)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_token_service(settings: AppSettings) -> JwtTokenService:
    return JwtTokenService(
        secret_key=settings.security.secret_key,
        expire_minutes=settings.security.token_expiration_minutes,
    )


async def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DbSession,
    token_service: JwtTokenService = Depends(get_token_service),  # pyright: ignore[reportCallInDefaultInitializer]
) -> uuid.UUID:
    try:
        user_id = token_service.decode_access_token(token)
    except (InvalidTokenError, ExpiredTokenError) as exc:
        raise credentials_exception from exc

    user = await AsyncSqlAlchemyUserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user_id


type CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
type TokenSvc = Annotated[JwtTokenService, Depends(get_token_service)]


def get_user_repo(session: DbSession) -> AsyncSqlAlchemyUserRepository:
    return AsyncSqlAlchemyUserRepository(session)


def get_plan_repo(session: DbSession) -> AsyncSqlAlchemyPlanRepository:
    return AsyncSqlAlchemyPlanRepository(session)


def get_profile_repo(session: DbSession) -> AsyncSqlAlchemyProfileRepository:
    return AsyncSqlAlchemyProfileRepository(session)


def get_schedule_repo(session: DbSession) -> AsyncSqlAlchemyScheduleRepository:
    return AsyncSqlAlchemyScheduleRepository(session)


def get_refresh_token_repo(session: DbSession) -> AsyncSqlAlchemyRefreshTokenRepository:
    return AsyncSqlAlchemyRefreshTokenRepository(session)


def get_account_token_repo(session: DbSession) -> AsyncSqlAlchemyAccountTokenRepository:
    return AsyncSqlAlchemyAccountTokenRepository(session)


type UserRepo = Annotated[AsyncSqlAlchemyUserRepository, Depends(get_user_repo)]
type PlanRepo = Annotated[AsyncSqlAlchemyPlanRepository, Depends(get_plan_repo)]
type ProfileRepo = Annotated[AsyncSqlAlchemyProfileRepository, Depends(get_profile_repo)]
type ScheduleRepo = Annotated[AsyncSqlAlchemyScheduleRepository, Depends(get_schedule_repo)]
type RefreshTokenRepo = Annotated[AsyncSqlAlchemyRefreshTokenRepository, Depends(get_refresh_token_repo)]
type AccountTokenRepo = Annotated[AsyncSqlAlchemyAccountTokenRepository, Depends(get_account_token_repo)]


def get_email_sender(settings: ApiConfig) -> EmailSender:
    email = settings.email
    if email.backend == "smtp":
        return SmtpEmailSender(
            host=email.host,
            port=email.port,
            sender=email.sender,
            username=email.username,
            password=email.password,
            starttls=email.starttls,
            use_ssl=email.use_ssl,
        )
    return ConsoleEmailSender()


class BackgroundEmailSender:
    """Delivers mail after the response so response timing does not reveal whether an account exists."""

    def __init__(self, tasks: BackgroundTasks, sender: EmailSender) -> None:
        self._tasks: BackgroundTasks = tasks
        self._sender: EmailSender = sender

    async def send(self, message: EmailMessage) -> None:
        self._tasks.add_task(self._deliver, message)

    async def _deliver(self, message: EmailMessage) -> None:
        try:
            await self._sender.send(message)
        except Exception:
            await logger.aexception("email_delivery_failed", to=message.to, subject=message.subject)  # pyright: ignore[reportAny]


def get_background_email_sender(
    tasks: BackgroundTasks,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> BackgroundEmailSender:
    return BackgroundEmailSender(tasks, sender)


type Mailer = Annotated[BackgroundEmailSender, Depends(get_background_email_sender)]


def get_rate_limiter(request: Request, settings: ApiConfig) -> RateLimiter:
    limiter: RateLimiter | None = getattr(request.app.state, "rate_limiter", None)  # pyright: ignore[reportAny]
    if limiter is None:
        config = settings.rate_limit
        if config.backend == "redis":
            limiter = RedisRateLimiter(Redis.from_url(config.redis_url))
        else:
            limiter = InMemoryRateLimiter()
        request.app.state.rate_limiter = limiter
    return limiter


type Limiter = Annotated[RateLimiter, Depends(get_rate_limiter)]


class RateLimit:
    """Callable that enforces a fixed-window limit on an arbitrary key."""

    def __init__(self, limiter: RateLimiter, enabled: bool) -> None:
        self._limiter: RateLimiter = limiter
        self._enabled: bool = enabled

    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        if not self._enabled:
            return
        retry_after = await self._limiter.hit(key, limit, window_seconds)
        if retry_after is not None:
            raise RateLimitExceededError(retry_after)


def get_rate_limit(limiter: Limiter, settings: ApiConfig) -> RateLimit:
    return RateLimit(limiter, settings.rate_limit.enabled)


type RateLimitGuard = Annotated[RateLimit, Depends(get_rate_limit)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def per_ip_limit(scope: str, limit: int, window_seconds: int) -> Callable[..., Awaitable[None]]:
    async def dependency(request: Request, guard: RateLimitGuard) -> None:
        await guard.check(f"{scope}:ip:{client_ip(request)}", limit, window_seconds)

    return dependency


def get_register_user_handler(repo: UserRepo, hasher: PasswordHash) -> RegisterUserHandler:
    return RegisterUserHandler(user_repo=repo, password_hasher=hasher)


def get_authenticate_user_handler(repo: UserRepo, hasher: PasswordHash) -> AuthenticateUserHandler:
    return AuthenticateUserHandler(user_repo=repo, password_hasher=hasher)


def get_upsert_profile_handler(profiles: ProfileRepo, users: UserRepo) -> UpsertProfileHandler:
    return UpsertProfileHandler(profile_repo=profiles, user_repo=users)


type RegisterUser = Annotated[RegisterUserHandler, Depends(get_register_user_handler)]
type AuthenticateUser = Annotated[AuthenticateUserHandler, Depends(get_authenticate_user_handler)]
type UpsertProfile = Annotated[UpsertProfileHandler, Depends(get_upsert_profile_handler)]


def get_create_refresh_token_handler(
    repo: RefreshTokenRepo,
    token_service: TokenSvc,
    settings: AppSettings,
) -> CreateRefreshTokenHandler:
    return CreateRefreshTokenHandler(refresh_token_repo=repo, token_service=token_service, settings=settings)


def get_refresh_tokens_handler(
    repo: RefreshTokenRepo,
    token_service: TokenSvc,
    settings: AppSettings,
) -> RefreshTokensHandler:
    return RefreshTokensHandler(refresh_token_repo=repo, token_service=token_service, settings=settings)


def get_logout_handler(repo: RefreshTokenRepo, token_service: TokenSvc) -> LogoutHandler:
    return LogoutHandler(refresh_token_repo=repo, token_service=token_service)


type CreateRefreshToken = Annotated[CreateRefreshTokenHandler, Depends(get_create_refresh_token_handler)]
type RefreshTokens = Annotated[RefreshTokensHandler, Depends(get_refresh_tokens_handler)]
type Logout = Annotated[LogoutHandler, Depends(get_logout_handler)]


def get_get_user_handler(repo: UserRepo) -> GetUserHandler:
    return GetUserHandler(user_repo=repo)


def get_get_profile_handler(repo: ProfileRepo) -> GetProfileHandler:
    return GetProfileHandler(profile_repo=repo)


type GetUser = Annotated[GetUserHandler, Depends(get_get_user_handler)]
type GetProfile = Annotated[GetProfileHandler, Depends(get_get_profile_handler)]


def get_create_plan_handler(repo: PlanRepo, profiles: ProfileRepo) -> CreatePlanHandler:
    return CreatePlanHandler(plan_repo=repo, profile_repo=profiles)


def get_update_plan_handler(repo: PlanRepo) -> UpdatePlanHandler:
    return UpdatePlanHandler(plan_repo=repo)


def get_delete_plan_handler(repo: PlanRepo) -> DeletePlanHandler:
    return DeletePlanHandler(plan_repo=repo)


def get_save_plan_handler(repo: PlanRepo) -> SavePlanHandler:
    return SavePlanHandler(plan_repo=repo)


def get_add_extra_payment_handler(repo: PlanRepo) -> AddOneTimeExtraPaymentHandler:
    return AddOneTimeExtraPaymentHandler(plan_repo=repo)


def get_add_recurring_extra_payment_handler(repo: PlanRepo) -> AddRecurringExtraPaymentHandler:
    return AddRecurringExtraPaymentHandler(plan_repo=repo)


def get_add_interest_rate_change_handler(repo: PlanRepo) -> AddInterestRateChangeHandler:
    return AddInterestRateChangeHandler(plan_repo=repo)


def get_replace_adjustments_handler(repo: PlanRepo) -> ReplaceAdjustmentsHandler:
    return ReplaceAdjustmentsHandler(plan_repo=repo)


def get_duplicate_plan_handler(repo: PlanRepo) -> DuplicatePlanHandler:
    return DuplicatePlanHandler(plan_repo=repo)


type CreatePlan = Annotated[CreatePlanHandler, Depends(get_create_plan_handler)]
type ReplaceAdjustments = Annotated[ReplaceAdjustmentsHandler, Depends(get_replace_adjustments_handler)]
type DuplicatePlan = Annotated[DuplicatePlanHandler, Depends(get_duplicate_plan_handler)]
type UpdatePlan = Annotated[UpdatePlanHandler, Depends(get_update_plan_handler)]
type DeletePlan = Annotated[DeletePlanHandler, Depends(get_delete_plan_handler)]
type SavePlan = Annotated[SavePlanHandler, Depends(get_save_plan_handler)]
type AddExtraPayment = Annotated[AddOneTimeExtraPaymentHandler, Depends(get_add_extra_payment_handler)]
type AddRecurringExtraPayment = Annotated[
    AddRecurringExtraPaymentHandler, Depends(get_add_recurring_extra_payment_handler)
]
type AddInterestRateChange = Annotated[AddInterestRateChangeHandler, Depends(get_add_interest_rate_change_handler)]


def get_get_plan_handler(repo: PlanRepo) -> GetPlanHandler:
    return GetPlanHandler(plan_repo=repo)


def get_list_plans_handler(repo: PlanRepo) -> ListPlansHandler:
    return ListPlansHandler(plan_repo=repo)


type GetPlan = Annotated[GetPlanHandler, Depends(get_get_plan_handler)]
type ListPlans = Annotated[ListPlansHandler, Depends(get_list_plans_handler)]


def get_compare_plans_handler(repo: PlanRepo) -> ComparePlansHandler:
    return ComparePlansHandler(plan_repo=repo)


type ComparePlans = Annotated[ComparePlansHandler, Depends(get_compare_plans_handler)]


def get_generate_schedule_handler(plans: PlanRepo, schedules: ScheduleRepo) -> GenerateScheduleHandler:
    return GenerateScheduleHandler(plan_repo=plans, schedule_repo=schedules)


def get_save_schedule_handler(plans: PlanRepo, schedules: ScheduleRepo) -> SaveScheduleHandler:
    return SaveScheduleHandler(plan_repo=plans, schedule_repo=schedules)


def get_get_schedule_handler(schedules: ScheduleRepo, plans: PlanRepo) -> GetScheduleHandler:
    return GetScheduleHandler(schedule_repo=schedules, plan_repo=plans)


def get_list_schedules_handler(schedules: ScheduleRepo, plans: PlanRepo) -> ListSchedulesHandler:
    return ListSchedulesHandler(schedule_repo=schedules, plan_repo=plans)


def get_delete_schedule_handler(schedules: ScheduleRepo, plans: PlanRepo) -> DeleteScheduleHandler:
    return DeleteScheduleHandler(schedule_repo=schedules, plan_repo=plans)


type GenerateSchedule = Annotated[GenerateScheduleHandler, Depends(get_generate_schedule_handler)]
type SaveSchedule = Annotated[SaveScheduleHandler, Depends(get_save_schedule_handler)]
type GetSchedule = Annotated[GetScheduleHandler, Depends(get_get_schedule_handler)]
type ListSchedules = Annotated[ListSchedulesHandler, Depends(get_list_schedules_handler)]
type DeleteSchedule = Annotated[DeleteScheduleHandler, Depends(get_delete_schedule_handler)]


def get_send_verification_email_handler(
    users: UserRepo,
    tokens: AccountTokenRepo,
    token_service: TokenSvc,
    mailer: Mailer,
    settings: AppSettings,
) -> SendVerificationEmailHandler:
    return SendVerificationEmailHandler(
        user_repo=users, account_token_repo=tokens, token_service=token_service, email_sender=mailer, settings=settings
    )


def get_verify_email_handler(users: UserRepo, tokens: AccountTokenRepo, token_service: TokenSvc) -> VerifyEmailHandler:
    return VerifyEmailHandler(user_repo=users, account_token_repo=tokens, token_service=token_service)


def get_request_password_reset_handler(
    users: UserRepo,
    tokens: AccountTokenRepo,
    token_service: TokenSvc,
    mailer: Mailer,
    settings: AppSettings,
) -> RequestPasswordResetHandler:
    return RequestPasswordResetHandler(
        user_repo=users, account_token_repo=tokens, token_service=token_service, email_sender=mailer, settings=settings
    )


def get_reset_password_handler(
    users: UserRepo,
    tokens: AccountTokenRepo,
    refresh_tokens: RefreshTokenRepo,
    token_service: TokenSvc,
    hasher: PasswordHash,
) -> ResetPasswordHandler:
    return ResetPasswordHandler(
        user_repo=users,
        account_token_repo=tokens,
        refresh_token_repo=refresh_tokens,
        token_service=token_service,
        password_hasher=hasher,
    )


def get_change_password_handler(
    users: UserRepo, refresh_tokens: RefreshTokenRepo, hasher: PasswordHash
) -> ChangePasswordHandler:
    return ChangePasswordHandler(user_repo=users, refresh_token_repo=refresh_tokens, password_hasher=hasher)


def get_update_account_handler(users: UserRepo) -> UpdateAccountHandler:
    return UpdateAccountHandler(user_repo=users)


def get_revoke_all_sessions_handler(refresh_tokens: RefreshTokenRepo) -> RevokeAllSessionsHandler:
    return RevokeAllSessionsHandler(refresh_token_repo=refresh_tokens)


def get_delete_account_handler(users: UserRepo, hasher: PasswordHash) -> DeleteAccountHandler:
    return DeleteAccountHandler(user_repo=users, password_hasher=hasher)


def get_export_account_data_handler(
    users: UserRepo, profiles: ProfileRepo, plans: PlanRepo
) -> ExportAccountDataHandler:
    return ExportAccountDataHandler(user_repo=users, profile_repo=profiles, plan_repo=plans)


type SendVerificationEmail = Annotated[SendVerificationEmailHandler, Depends(get_send_verification_email_handler)]
type VerifyEmail = Annotated[VerifyEmailHandler, Depends(get_verify_email_handler)]
type RequestPasswordReset = Annotated[RequestPasswordResetHandler, Depends(get_request_password_reset_handler)]
type ResetPassword = Annotated[ResetPasswordHandler, Depends(get_reset_password_handler)]
type ChangePassword = Annotated[ChangePasswordHandler, Depends(get_change_password_handler)]
type UpdateAccount = Annotated[UpdateAccountHandler, Depends(get_update_account_handler)]
type RevokeAllSessions = Annotated[RevokeAllSessionsHandler, Depends(get_revoke_all_sessions_handler)]
type DeleteAccount = Annotated[DeleteAccountHandler, Depends(get_delete_account_handler)]
type ExportAccountData = Annotated[ExportAccountDataHandler, Depends(get_export_account_data_handler)]


def get_refinance_plan_handler(repo: PlanRepo) -> RefinancePlanHandler:
    return RefinancePlanHandler(plan_repo=repo)


def get_prepay_vs_invest_plan_handler(repo: PlanRepo) -> PrepayVsInvestPlanHandler:
    return PrepayVsInvestPlanHandler(plan_repo=repo)


type RefinancePlan = Annotated[RefinancePlanHandler, Depends(get_refinance_plan_handler)]
type PrepayVsInvestPlan = Annotated[PrepayVsInvestPlanHandler, Depends(get_prepay_vs_invest_plan_handler)]
