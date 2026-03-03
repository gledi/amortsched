"""Dependency injection container setup using rodi."""

from rodi import Container

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


def build_container() -> Container:
    """Build and return a fully wired rodi Container."""
    container = Container()

    store = InMemoryStore()
    user_repo = InMemoryUserRepository(store)
    plan_repo = InMemoryPlanRepository(store)
    schedule_repo = InMemoryScheduleRepository(store)
    profile_repo = InMemoryUserProfileRepository(store)
    hasher = PBKDF2PasswordHasher()
    token_service = JoseTokenService(secret_key=_SECRET_KEY)

    container.add_instance(store)
    container.add_instance(user_repo)
    container.add_instance(plan_repo)
    container.add_instance(schedule_repo)
    container.add_instance(profile_repo)
    container.add_instance(hasher)
    container.add_instance(token_service)

    # User handlers
    container.add_instance(RegisterUserHandler(user_repo=user_repo, password_hasher=hasher))
    container.add_instance(AuthenticateUserHandler(user_repo=user_repo, password_hasher=hasher))
    container.add_instance(GetUserHandler(user_repo=user_repo))
    container.add_instance(GetProfileHandler(profile_repo=profile_repo))
    container.add_instance(UpsertProfileHandler(profile_repo=profile_repo, user_repo=user_repo))

    # Plan handlers
    container.add_instance(CreatePlanHandler(plan_repo=plan_repo))
    container.add_instance(GetPlanHandler(plan_repo=plan_repo))
    container.add_instance(ListPlansHandler(plan_repo=plan_repo))
    container.add_instance(UpdatePlanHandler(plan_repo=plan_repo))
    container.add_instance(DeletePlanHandler(plan_repo=plan_repo))
    container.add_instance(SavePlanHandler(plan_repo=plan_repo))
    container.add_instance(AddInterestRateChangeHandler(plan_repo=plan_repo))
    container.add_instance(AddOneTimeExtraPaymentHandler(plan_repo=plan_repo))
    container.add_instance(AddRecurringExtraPaymentHandler(plan_repo=plan_repo))

    # Schedule handlers
    container.add_instance(GenerateScheduleHandler(plan_repo=plan_repo))
    container.add_instance(SaveScheduleHandler(plan_repo=plan_repo, schedule_repo=schedule_repo))
    container.add_instance(GetScheduleHandler(schedule_repo=schedule_repo, plan_repo=plan_repo))
    container.add_instance(ListSchedulesHandler(schedule_repo=schedule_repo, plan_repo=plan_repo))
    container.add_instance(DeleteScheduleHandler(schedule_repo=schedule_repo, plan_repo=plan_repo))

    return container
