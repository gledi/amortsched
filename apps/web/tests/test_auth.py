"""Auth endpoint tests for FastAPI web app."""

import pytest

pytestmark = pytest.mark.anyio


async def test_register_returns_user_and_token(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "name": "User", "password": "pass123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == "user@example.com"
    assert "token" in data


async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={"email": "dup@e.com", "name": "U", "password": "p"})
    resp = await client.post("/api/auth/register", json={"email": "dup@e.com", "name": "U2", "password": "p2"})
    assert resp.status_code == 409


async def test_login_success(client):
    await client.post("/api/auth/register", json={"email": "l@e.com", "name": "U", "password": "pass"})
    resp = await client.post("/api/auth/login", json={"email": "l@e.com", "password": "pass"})
    assert resp.status_code == 200
    assert "token" in resp.json()


async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={"email": "f@e.com", "name": "U", "password": "correct"})
    resp = await client.post("/api/auth/login", json={"email": "f@e.com", "password": "wrong"})
    assert resp.status_code == 401


async def test_protected_endpoint_without_token(client):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_protected_endpoint_with_invalid_token(client):
    resp = await client.get("/api/users/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401
