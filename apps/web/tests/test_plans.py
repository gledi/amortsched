"""Plan endpoint tests for FastAPI web app."""

import pytest

pytestmark = pytest.mark.anyio

PLAN_DATA = {
    "name": "Test Plan",
    "amount": "100000",
    "interestRate": "5.5",
    "term": {"years": 10, "months": 0},
    "startDate": "2026-01-15",
}


async def _create_plan(client, headers):
    resp = await client.post("/api/plans", json=PLAN_DATA, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_create_plan(client, auth_headers):
    data = await _create_plan(client, auth_headers)
    assert data["name"] == "Test Plan"
    assert data["status"] == "draft"


async def test_list_plans(client, auth_headers):
    await _create_plan(client, auth_headers)
    resp = await client.get("/api/plans", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_get_plan(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.get(f"/api/plans/{plan['id']}", headers=auth_headers)
    assert resp.status_code == 200


async def test_update_plan(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.put(f"/api/plans/{plan['id']}", json={"name": "Updated"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


async def test_delete_plan(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.delete(f"/api/plans/{plan['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_save_plan(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(f"/api/plans/{plan['id']}/save", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"


async def test_add_extra_payment(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(
        f"/api/plans/{plan['id']}/extra-payments",
        json={"date": "2026-06-15", "amount": "5000"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_add_recurring_extra_payment(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(
        f"/api/plans/{plan['id']}/recurring-extra-payments",
        json={"startDate": "2026-06-15", "amount": "1000", "count": 6},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_add_interest_rate_change(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(
        f"/api/plans/{plan['id']}/interest-rate-changes",
        json={"effectiveDate": "2027-01-15", "rate": "4.5"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_plan_ownership(client, register_user):
    token1 = await register_user(client, "owner@e.com")
    h1 = {"Authorization": f"Bearer {token1}"}
    plan = await _create_plan(client, h1)

    token2 = await register_user(client, "other@e.com")
    h2 = {"Authorization": f"Bearer {token2}"}
    resp = await client.get(f"/api/plans/{plan['id']}", headers=h2)
    assert resp.status_code == 403
