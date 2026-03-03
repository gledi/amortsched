"""User and profile endpoint tests for FastAPI web app."""

import pytest

pytestmark = pytest.mark.anyio


async def test_get_me(client, auth_headers):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


async def test_get_profile_not_found(client, auth_headers):
    resp = await client.get("/api/users/me/profile", headers=auth_headers)
    assert resp.status_code == 404


async def test_upsert_profile_create(client, auth_headers):
    resp = await client.put(
        "/api/users/me/profile",
        json={"displayName": "Test User", "locale": "en-US"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["displayName"] == "Test User"


async def test_upsert_profile_update(client, auth_headers):
    await client.put("/api/users/me/profile", json={"displayName": "Original"}, headers=auth_headers)
    resp = await client.put(
        "/api/users/me/profile",
        json={"displayName": "Updated", "phone": "+1234"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["displayName"] == "Updated"


async def test_get_profile_after_create(client, auth_headers):
    await client.put("/api/users/me/profile", json={"displayName": "Me"}, headers=auth_headers)
    resp = await client.get("/api/users/me/profile", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["displayName"] == "Me"
