import httpx
import pytest
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from amortsched.adapters.persistence.tables import metadata
from amortsched.api.app import create_app
from amortsched.api.config import get_settings


@pytest.fixture
def database_url(postgres):
    url = postgres.get_connection_url(driver="psycopg")
    engine = create_sync_engine(url)
    metadata.drop_all(engine, checkfirst=True)
    metadata.create_all(engine)
    yield url
    metadata.drop_all(engine, checkfirst=True)
    engine.dispose()


@pytest.fixture
async def client(database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    async_url = database_url.replace("+psycopg://", "+psycopg_async://")

    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = create_app()
    app.state.async_session_factory = session_factory

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c

    await engine.dispose()


async def _register_and_get_token(client: httpx.AsyncClient, email: str = "test@example.com") -> str:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "name": "Test User", "password": "testpass123"},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


@pytest.fixture
def register_user():
    return _register_and_get_token


@pytest.fixture
async def auth_headers(client):
    token = await _register_and_get_token(client)
    return {"Authorization": f"Bearer {token}"}
