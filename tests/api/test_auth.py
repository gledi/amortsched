import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "name": "Test User", "password": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_login(client, register_user):
    await register_user(client, "login@example.com")
    resp = await client.post(
        "/api/auth/token",
        data={"username": "login@example.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, register_user):
    await register_user(client, "wrong@example.com")
    resp = await client.post(
        "/api/auth/token",
        data={"username": "wrong@example.com", "password": "wrongpassword"},
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


@pytest.mark.asyncio
async def test_refresh_token(client, register_user):
    await register_user(client, "refresh@example.com")
    login_resp = await client.post(
        "/api/auth/token",
        data={"username": "refresh@example.com", "password": "testpass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_token_rotation_invalidates_old(client, register_user):
    await register_user(client, "rotate@example.com")
    login_resp = await client.post(
        "/api/auth/token",
        data={"username": "rotate@example.com", "password": "testpass123"},
    )
    old_refresh = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200

    resp = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_replay_revokes_family(client, register_user):
    await register_user(client, "replay@example.com")
    login_resp = await client.post(
        "/api/auth/token",
        data={"username": "replay@example.com", "password": "testpass123"},
    )
    old_refresh = login_resp.json()["refresh_token"]

    refresh_resp = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    new_refresh = refresh_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401

    resp = await client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, register_user):
    await register_user(client, "logout@example.com")
    login_resp = await client.post(
        "/api/auth/token",
        data={"username": "logout@example.com", "password": "testpass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 204

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client):
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "invalid-token"})
    assert resp.status_code == 401
