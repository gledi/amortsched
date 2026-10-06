import httpx2 as httpx
import pytest
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from amortsched.adapters.persistence.tables import metadata
from amortsched.api.app import create_app
from amortsched.api.config import get_settings
from amortsched.api.dependencies import get_email_sender
from amortsched.app.ports import EmailMessage


class Outbox:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)

    def last_token(self, to: str) -> str:
        message = next(m for m in reversed(self.messages) if m.to == to)
        return message.text.split("token=", 1)[1].split()[0]


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
def outbox() -> Outbox:
    return Outbox()


@pytest.fixture
async def client(database_url, monkeypatch, outbox):
    monkeypatch.setenv("DATABASE__DSN", database_url)
    monkeypatch.setenv("SECURITY__SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
    monkeypatch.setenv("SECURITY__COOKIE_SECURE", "false")
    get_settings.cache_clear()

    async_url = database_url.replace("+psycopg://", "+psycopg_async://")

    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = create_app()
    app.state.async_session_factory = session_factory
    app.dependency_overrides[get_email_sender] = lambda: outbox

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
