"""Test fixtures for the FastAPI web app."""

import httpx
import pytest
from amortsched.auth import JoseTokenService
from amortsched.core.security import PBKDF2PasswordHasher
from amortsched.data.inmemory import (
    InMemoryPlanRepository,
    InMemoryScheduleRepository,
    InMemoryStore,
    InMemoryUserProfileRepository,
    InMemoryUserRepository,
)
from amortsched.web import deps
from amortsched.web.app import app

_SECRET = "test-secret-key"


@pytest.fixture(autouse=True)
def _fresh_store():
    """Replace module-level singletons with fresh instances per test."""
    store = InMemoryStore()
    deps._store = store
    deps._user_repo = InMemoryUserRepository(store)
    deps._plan_repo = InMemoryPlanRepository(store)
    deps._schedule_repo = InMemoryScheduleRepository(store)
    deps._profile_repo = InMemoryUserProfileRepository(store)
    deps._hasher = PBKDF2PasswordHasher()
    deps._token_service = JoseTokenService(secret_key=_SECRET)


@pytest.fixture
def client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


async def _register_and_get_token(client: httpx.AsyncClient, email: str = "test@example.com") -> str:
    """Register a user and return the Bearer token."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "name": "Test User", "password": "testpass123"},
    )
    assert resp.status_code == 201
    return resp.json()["token"]


@pytest.fixture
def register_user():
    """Fixture returning async helper to register a user and get a token."""
    return _register_and_get_token


@pytest.fixture
async def auth_headers(client):
    """Register a user and return auth headers."""
    token = await _register_and_get_token(client)
    return {"Authorization": f"Bearer {token}"}
