import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from amortsched.adapters.persistence.repositories import (
    AsyncSqlAlchemyPlanRepository,
    AsyncSqlAlchemyProfileRepository,
    AsyncSqlAlchemyRefreshTokenRepository,
    AsyncSqlAlchemyScheduleRepository,
    AsyncSqlAlchemyUserRepository,
)
from amortsched.adapters.security.hashers import PBKDF2PasswordHasher
from amortsched.adapters.security.tokens import JwtTokenService
from amortsched.api.config import get_settings
from amortsched.app.commands.plans import (
    AddInterestRateChangeHandler,
    AddOneTimeExtraPaymentHandler,
    AddRecurringExtraPaymentHandler,
    CreatePlanHandler,
    DeletePlanHandler,
    DeleteScheduleHandler,
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
from amortsched.app.ports import Settings
from amortsched.app.queries.comparisons import ComparePlansHandler
from amortsched.app.queries.plans import GetPlanHandler, ListPlansHandler
from amortsched.app.queries.schedules import GenerateScheduleHandler, GetScheduleHandler, ListSchedulesHandler
from amortsched.app.queries.users import GetProfileHandler, GetUserHandler
from amortsched.core.errors import ExpiredTokenError, InvalidTokenError, RefreshTokenReplayError


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


type DbSession = Annotated[AsyncSession, Depends(get_session)]
type AppSettings = Annotated[Settings, Depends(get_settings)]
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


type UserRepo = Annotated[AsyncSqlAlchemyUserRepository, Depends(get_user_repo)]
type PlanRepo = Annotated[AsyncSqlAlchemyPlanRepository, Depends(get_plan_repo)]
type ProfileRepo = Annotated[AsyncSqlAlchemyProfileRepository, Depends(get_profile_repo)]
type ScheduleRepo = Annotated[AsyncSqlAlchemyScheduleRepository, Depends(get_schedule_repo)]
type RefreshTokenRepo = Annotated[AsyncSqlAlchemyRefreshTokenRepository, Depends(get_refresh_token_repo)]


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


def get_create_plan_handler(repo: PlanRepo) -> CreatePlanHandler:
    return CreatePlanHandler(plan_repo=repo)


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


type CreatePlan = Annotated[CreatePlanHandler, Depends(get_create_plan_handler)]
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
