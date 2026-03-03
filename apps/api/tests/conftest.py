"""Test fixtures for the Starlette API app."""

import httpx
import pytest
from amortsched.api.app import app
from amortsched.api.deps import build_container


@pytest.fixture
def container():
    """Build a fresh DI container for each test."""
    return build_container()


@pytest.fixture
def client(container):
    """AsyncClient with a fresh DI container."""
    app.state.container = container
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


async def _register_and_get_token(client: httpx.AsyncClient, email: str = "test@example.com") -> str:
    """Register a user and return the Bearer token."""
    resp = await client.post(
        "/api/auth/register",
        content=b'{"email": "' + email.encode() + b'", "name": "Test User", "password": "testpass123"}',
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
