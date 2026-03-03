import pytest
from amortsched.core.security import PBKDF2PasswordHasher
from amortsched.data.inmemory.repositories import (
    InMemoryPlanRepository,
    InMemoryScheduleRepository,
    InMemoryUserProfileRepository,
    InMemoryUserRepository,
)
from amortsched.data.inmemory.store import InMemoryStore


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def user_repo(store):
    return InMemoryUserRepository(store)


@pytest.fixture
def plan_repo(store):
    return InMemoryPlanRepository(store)


@pytest.fixture
def schedule_repo(store):
    return InMemoryScheduleRepository(store)


@pytest.fixture
def profile_repo(store):
    return InMemoryUserProfileRepository(store)


@pytest.fixture
def password_hasher():
    return PBKDF2PasswordHasher()
