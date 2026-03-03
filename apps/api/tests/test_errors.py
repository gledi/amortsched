"""Error response format tests for Starlette API."""

import pytest

pytestmark = pytest.mark.anyio


async def test_not_found_is_problem_json(client, auth_headers):
    resp = await client.get("/api/plans/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.headers["content-type"] == "application/problem+json"
    body = resp.json()
    assert body["type"] == "urn:amortsched/errors/not-found"
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    assert "detail" in body


async def test_auth_error_is_problem_json(client):
    await client.post(
        "/api/auth/register",
        content=b'{"email": "e@e.com", "name": "U", "password": "p"}',
    )
    resp = await client.post(
        "/api/auth/login",
        content=b'{"email": "e@e.com", "password": "wrong"}',
    )
    assert resp.status_code == 401
    assert resp.headers["content-type"] == "application/problem+json"


async def test_duplicate_email_is_problem_json(client):
    await client.post(
        "/api/auth/register",
        content=b'{"email": "d@d.com", "name": "U", "password": "p"}',
    )
    resp = await client.post(
        "/api/auth/register",
        content=b'{"email": "d@d.com", "name": "U2", "password": "p2"}',
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["type"] == "urn:amortsched/errors/duplicate-email"
    assert body["status"] == 409
