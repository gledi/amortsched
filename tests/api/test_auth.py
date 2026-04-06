import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "name": "Test User", "password": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["user"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_login(client, register_user):
    await register_user(client, "login@example.com")
    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client, register_user):
    await register_user(client, "wrong@example.com")
    resp = await client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_email(client, register_user):
    await register_user(client, "dup@example.com")
    resp = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "name": "Another", "password": "pass123"},
    )
    assert resp.status_code == 409
