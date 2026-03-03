"""User and profile endpoint tests for Starlette API."""

import orjson
import pytest

pytestmark = pytest.mark.anyio


async def test_get_me(client, auth_headers):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["isActive"] is True


async def test_get_profile_not_found(client, auth_headers):
    resp = await client.get("/api/users/me/profile", headers=auth_headers)
    assert resp.status_code == 404


async def test_upsert_profile_create(client, auth_headers):
    resp = await client.put(
        "/api/users/me/profile",
        content=orjson.dumps({"displayName": "Test User", "locale": "en-US"}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["displayName"] == "Test User"
    assert data["locale"] == "en-US"


async def test_upsert_profile_update(client, auth_headers):
    await client.put(
        "/api/users/me/profile",
        content=orjson.dumps({"displayName": "Original"}),
        headers=auth_headers,
    )
    resp = await client.put(
        "/api/users/me/profile",
        content=orjson.dumps({"displayName": "Updated", "phone": "+1234"}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["displayName"] == "Updated"
    assert data["phone"] == "+1234"


async def test_get_profile_after_create(client, auth_headers):
    await client.put(
        "/api/users/me/profile",
        content=orjson.dumps({"displayName": "Me"}),
        headers=auth_headers,
    )
    resp = await client.get("/api/users/me/profile", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["displayName"] == "Me"
