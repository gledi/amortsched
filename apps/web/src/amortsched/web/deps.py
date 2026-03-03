"""Dependency injection factories for FastAPI."""

from amortsched.app.plans import (
    AddInterestRateChangeHandler,
    AddOneTimeExtraPaymentHandler,
    AddRecurringExtraPaymentHandler,
    CreatePlanHandler,
    DeletePlanHandler,
    DeleteScheduleHandler,
    GenerateScheduleHandler,
    GetPlanHandler,
    GetScheduleHandler,
    ListPlansHandler,
    ListSchedulesHandler,
    SavePlanHandler,
    SaveScheduleHandler,
    UpdatePlanHandler,
)
from amortsched.app.users import (
    AuthenticateUserHandler,
    GetProfileHandler,
    GetUserHandler,
    RegisterUserHandler,
    UpsertProfileHandler,
)
from amortsched.auth import JoseTokenService
from amortsched.core.security import PBKDF2PasswordHasher
from amortsched.data.inmemory import (
    InMemoryPlanRepository,
    InMemoryScheduleRepository,
    InMemoryStore,
    InMemoryUserProfileRepository,
    InMemoryUserRepository,
)

# TODO: load from environment variable in production
_SECRET_KEY = "amortsched-dev-secret-key-change-in-production"

_store = InMemoryStore()
_user_repo = InMemoryUserRepository(_store)
_plan_repo = InMemoryPlanRepository(_store)
_schedule_repo = InMemoryScheduleRepository(_store)
_profile_repo = InMemoryUserProfileRepository(_store)
_hasher = PBKDF2PasswordHasher()
_token_service = JoseTokenService(secret_key=_SECRET_KEY)


def get_token_service() -> JoseTokenService:
    return _token_service


def get_register_user_handler() -> RegisterUserHandler:
    return RegisterUserHandler(user_repo=_user_repo, password_hasher=_hasher)


def get_authenticate_user_handler() -> AuthenticateUserHandler:
    return AuthenticateUserHandler(user_repo=_user_repo, password_hasher=_hasher)


def get_user_handler() -> GetUserHandler:
    return GetUserHandler(user_repo=_user_repo)


def get_profile_handler() -> GetProfileHandler:
    return GetProfileHandler(profile_repo=_profile_repo)


def get_upsert_profile_handler() -> UpsertProfileHandler:
    return UpsertProfileHandler(profile_repo=_profile_repo, user_repo=_user_repo)


def get_create_plan_handler() -> CreatePlanHandler:
    return CreatePlanHandler(plan_repo=_plan_repo)


def get_plan_handler() -> GetPlanHandler:
    return GetPlanHandler(plan_repo=_plan_repo)


def get_list_plans_handler() -> ListPlansHandler:
    return ListPlansHandler(plan_repo=_plan_repo)


def get_update_plan_handler() -> UpdatePlanHandler:
    return UpdatePlanHandler(plan_repo=_plan_repo)


def get_delete_plan_handler() -> DeletePlanHandler:
    return DeletePlanHandler(plan_repo=_plan_repo)


def get_save_plan_handler() -> SavePlanHandler:
    return SavePlanHandler(plan_repo=_plan_repo)


def get_add_interest_rate_change_handler() -> AddInterestRateChangeHandler:
    return AddInterestRateChangeHandler(plan_repo=_plan_repo)


def get_add_one_time_extra_payment_handler() -> AddOneTimeExtraPaymentHandler:
    return AddOneTimeExtraPaymentHandler(plan_repo=_plan_repo)


def get_add_recurring_extra_payment_handler() -> AddRecurringExtraPaymentHandler:
    return AddRecurringExtraPaymentHandler(plan_repo=_plan_repo)


def get_generate_schedule_handler() -> GenerateScheduleHandler:
    return GenerateScheduleHandler(plan_repo=_plan_repo)


def get_save_schedule_handler() -> SaveScheduleHandler:
    return SaveScheduleHandler(plan_repo=_plan_repo, schedule_repo=_schedule_repo)


def get_schedule_handler() -> GetScheduleHandler:
    return GetScheduleHandler(schedule_repo=_schedule_repo, plan_repo=_plan_repo)


def get_list_schedules_handler() -> ListSchedulesHandler:
    return ListSchedulesHandler(schedule_repo=_schedule_repo, plan_repo=_plan_repo)


def get_delete_schedule_handler() -> DeleteScheduleHandler:
    return DeleteScheduleHandler(schedule_repo=_schedule_repo, plan_repo=_plan_repo)
