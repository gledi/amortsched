"""Error response format tests for FastAPI web app."""

import pytest

pytestmark = pytest.mark.anyio


async def test_not_found_is_problem_json(client, auth_headers):
    resp = await client.get("/api/plans/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.headers["content-type"] == "application/problem+json"
    body = resp.json()
    assert body["type"] == "urn:amortsched/errors/not-found"
    assert body["status"] == 404


async def test_duplicate_email_is_problem_json(client):
    await client.post("/api/auth/register", json={"email": "d@d.com", "name": "U", "password": "p"})
    resp = await client.post("/api/auth/register", json={"email": "d@d.com", "name": "U2", "password": "p2"})
    assert resp.status_code == 409
    assert resp.headers["content-type"] == "application/problem+json"
