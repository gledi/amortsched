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


def test_validation_error_returns_422():
    from amortsched.core.errors import ValidationError
    from amortsched.web.errors import domain_error_to_problem

    err = ValidationError([{"field": "email", "message": "required"}])
    status, body = domain_error_to_problem(err)
    assert status == 422
    assert body["type"] == "urn:amortsched/errors/validation-error"
    assert body["title"] == "Validation Error"
    assert body["errors"] == [{"field": "email", "message": "required"}]
