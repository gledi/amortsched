import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from amortsched.adapters.persistence.repositories import (
    AsyncSqlAlchemyPlanRepository,
    AsyncSqlAlchemyProfileRepository,
    AsyncSqlAlchemyScheduleRepository,
    AsyncSqlAlchemyUserRepository,
)
from amortsched.adapters.security.jwt import JoseTokenService
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
    RegisterUserHandler,
    UpsertProfileHandler,
)
from amortsched.app.queries.plans import GetPlanHandler, ListPlansHandler
from amortsched.app.queries.schedules import (
    GenerateScheduleHandler,
    GetScheduleHandler,
    ListSchedulesHandler,
)
from amortsched.app.queries.users import GetProfileHandler, GetUserHandler
from amortsched.core.errors import InvalidTokenError
from amortsched.core.security import PBKDF2PasswordHasher


def get_token_service() -> JoseTokenService:
    settings = get_settings()
    return JoseTokenService(
        secret_key=settings.secret_key,
        expire_minutes=settings.token_expiration_minutes,
    )


def get_password_hasher() -> PBKDF2PasswordHasher:
    return PBKDF2PasswordHasher()


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.async_session_factory() as session:
        yield session
        await session.commit()


async def get_current_user_id(
    authorization: str = Header(),
    token_service: JoseTokenService = Depends(get_token_service),
) -> uuid.UUID:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidTokenError("Invalid authorization header")
    return token_service.decode_access_token(token)


# --- User command handlers ---


def get_register_user_handler(
    session: AsyncSession = Depends(get_session),
    password_hasher: PBKDF2PasswordHasher = Depends(get_password_hasher),
) -> RegisterUserHandler:
    return RegisterUserHandler(
        user_repo=AsyncSqlAlchemyUserRepository(session),
        password_hasher=password_hasher,
    )


def get_authenticate_user_handler(
    session: AsyncSession = Depends(get_session),
    password_hasher: PBKDF2PasswordHasher = Depends(get_password_hasher),
) -> AuthenticateUserHandler:
    return AuthenticateUserHandler(
        user_repo=AsyncSqlAlchemyUserRepository(session),
        password_hasher=password_hasher,
    )


def get_upsert_profile_handler(session: AsyncSession = Depends(get_session)) -> UpsertProfileHandler:
    return UpsertProfileHandler(
        profile_repo=AsyncSqlAlchemyProfileRepository(session),
        user_repo=AsyncSqlAlchemyUserRepository(session),
    )


# --- User query handlers ---


def get_get_user_handler(session: AsyncSession = Depends(get_session)) -> GetUserHandler:
    return GetUserHandler(user_repo=AsyncSqlAlchemyUserRepository(session))


def get_get_profile_handler(session: AsyncSession = Depends(get_session)) -> GetProfileHandler:
    return GetProfileHandler(profile_repo=AsyncSqlAlchemyProfileRepository(session))


# --- Plan command handlers ---


def get_create_plan_handler(session: AsyncSession = Depends(get_session)) -> CreatePlanHandler:
    return CreatePlanHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_update_plan_handler(session: AsyncSession = Depends(get_session)) -> UpdatePlanHandler:
    return UpdatePlanHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_delete_plan_handler(session: AsyncSession = Depends(get_session)) -> DeletePlanHandler:
    return DeletePlanHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_save_plan_handler(session: AsyncSession = Depends(get_session)) -> SavePlanHandler:
    return SavePlanHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_add_extra_payment_handler(session: AsyncSession = Depends(get_session)) -> AddOneTimeExtraPaymentHandler:
    return AddOneTimeExtraPaymentHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_add_recurring_extra_payment_handler(
    session: AsyncSession = Depends(get_session),
) -> AddRecurringExtraPaymentHandler:
    return AddRecurringExtraPaymentHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_add_interest_rate_change_handler(
    session: AsyncSession = Depends(get_session),
) -> AddInterestRateChangeHandler:
    return AddInterestRateChangeHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


# --- Plan query handlers ---


def get_get_plan_handler(session: AsyncSession = Depends(get_session)) -> GetPlanHandler:
    return GetPlanHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_list_plans_handler(session: AsyncSession = Depends(get_session)) -> ListPlansHandler:
    return ListPlansHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


# --- Schedule handlers ---


def get_generate_schedule_handler(session: AsyncSession = Depends(get_session)) -> GenerateScheduleHandler:
    return GenerateScheduleHandler(plan_repo=AsyncSqlAlchemyPlanRepository(session))


def get_save_schedule_handler(session: AsyncSession = Depends(get_session)) -> SaveScheduleHandler:
    return SaveScheduleHandler(
        plan_repo=AsyncSqlAlchemyPlanRepository(session),
        schedule_repo=AsyncSqlAlchemyScheduleRepository(session),
    )


def get_get_schedule_handler(session: AsyncSession = Depends(get_session)) -> GetScheduleHandler:
    return GetScheduleHandler(
        schedule_repo=AsyncSqlAlchemyScheduleRepository(session),
        plan_repo=AsyncSqlAlchemyPlanRepository(session),
    )


def get_list_schedules_handler(session: AsyncSession = Depends(get_session)) -> ListSchedulesHandler:
    return ListSchedulesHandler(
        schedule_repo=AsyncSqlAlchemyScheduleRepository(session),
        plan_repo=AsyncSqlAlchemyPlanRepository(session),
    )


def get_delete_schedule_handler(session: AsyncSession = Depends(get_session)) -> DeleteScheduleHandler:
    return DeleteScheduleHandler(
        schedule_repo=AsyncSqlAlchemyScheduleRepository(session),
        plan_repo=AsyncSqlAlchemyPlanRepository(session),
    )
