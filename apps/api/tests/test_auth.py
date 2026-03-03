"""Auth endpoint tests for Starlette API."""

import pytest

pytestmark = pytest.mark.anyio


async def test_register_returns_user_and_token(client):
    resp = await client.post(
        "/api/auth/register",
        content=b'{"email": "user@example.com", "name": "User", "password": "pass123"}',
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["name"] == "User"
    assert data["user"]["isActive"] is True
    assert "token" in data


async def test_register_duplicate_email(client):
    await client.post(
        "/api/auth/register",
        content=b'{"email": "dup@example.com", "name": "User", "password": "pass"}',
    )
    resp = await client.post(
        "/api/auth/register",
        content=b'{"email": "dup@example.com", "name": "User2", "password": "pass"}',
    )
    assert resp.status_code == 409
    assert resp.json()["type"] == "urn:amortsched/errors/duplicate-email"


async def test_login_success(client):
    await client.post(
        "/api/auth/register",
        content=b'{"email": "login@example.com", "name": "User", "password": "pass123"}',
    )
    resp = await client.post(
        "/api/auth/login",
        content=b'{"email": "login@example.com", "password": "pass123"}',
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "login@example.com"
    assert "token" in data


async def test_login_wrong_password(client):
    await client.post(
        "/api/auth/register",
        content=b'{"email": "fail@example.com", "name": "User", "password": "correct"}',
    )
    resp = await client.post(
        "/api/auth/login",
        content=b'{"email": "fail@example.com", "password": "wrong"}',
    )
    assert resp.status_code == 401
    assert resp.json()["type"] == "urn:amortsched/errors/authentication-failed"


async def test_login_nonexistent_email(client):
    resp = await client.post(
        "/api/auth/login",
        content=b'{"email": "noone@example.com", "password": "pass"}',
    )
    assert resp.status_code == 401


async def test_protected_endpoint_without_token(client):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_protected_endpoint_with_invalid_token(client):
    resp = await client.get("/api/users/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401
