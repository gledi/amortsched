import datetime

import pytest

from amortsched.repositories import PlanRepository, UserRepository
from amortsched.security import PBKDF2PasswordHasher
from amortsched.services import PlanService, UserService


@pytest.fixture
def user_repo():
    return UserRepository()


@pytest.fixture
def plan_repo():
    return PlanRepository()


@pytest.fixture
def password_hasher():
    return PBKDF2PasswordHasher()


@pytest.fixture
def user_service(user_repo, password_hasher):
    return UserService(user_repo, password_hasher)


@pytest.fixture
def plan_service(plan_repo):
    return PlanService(plan_repo)


@pytest.fixture
def sample_user(user_service):
    return user_service.register(email="alice@example.com", name="Alice Smith", password="s3cret!")


@pytest.fixture
def sample_plan(plan_service, sample_user):
    return plan_service.create_plan(
        user_id=sample_user.id,
        name="Home Loan",
        amount=300_000,
        term=30,
        interest_rate=5.5,
        start_date=datetime.date(2025, 1, 1),
    )
