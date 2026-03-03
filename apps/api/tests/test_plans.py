"""Plan endpoint tests for Starlette API."""

import orjson
import pytest

pytestmark = pytest.mark.anyio

PLAN_PAYLOAD = orjson.dumps(
    {
        "name": "Test Plan",
        "amount": "100000",
        "interestRate": "5.5",
        "term": {"years": 10, "months": 0},
        "startDate": "2026-01-15",
    }
)


async def _create_plan(client, headers):
    resp = await client.post("/api/plans", content=PLAN_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_create_plan(client, auth_headers):
    data = await _create_plan(client, auth_headers)
    assert data["name"] == "Test Plan"
    assert data["status"] == "draft"
    assert "id" in data


async def test_list_plans(client, auth_headers):
    await _create_plan(client, auth_headers)
    await _create_plan(client, auth_headers)
    resp = await client.get("/api/plans", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_get_plan(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.get(f"/api/plans/{plan['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == plan["id"]


async def test_update_plan(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.put(
        f"/api/plans/{plan['id']}",
        content=orjson.dumps({"name": "Updated"}),
        headers=auth_headers,
    )
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
        content=orjson.dumps({"date": "2026-06-15", "amount": "5000"}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["oneTimeExtraPayments"]) == 1


async def test_add_recurring_extra_payment(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(
        f"/api/plans/{plan['id']}/recurring-extra-payments",
        content=orjson.dumps({"startDate": "2026-06-15", "amount": "1000", "count": 6}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["recurringExtraPayments"]) == 1


async def test_add_interest_rate_change(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(
        f"/api/plans/{plan['id']}/interest-rate-changes",
        content=orjson.dumps({"effectiveDate": "2027-01-15", "rate": "4.5"}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["interestRateChanges"]) == 1


async def test_get_plan_not_found(client, auth_headers):
    resp = await client.get("/api/plans/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404


async def test_plan_ownership(client, container, register_user):
    """Creating with one user, accessing with another should 403."""
    token1 = await register_user(client, "owner@example.com")
    headers1 = {"Authorization": f"Bearer {token1}"}
    plan = await _create_plan(client, headers1)

    token2 = await register_user(client, "other@example.com")
    headers2 = {"Authorization": f"Bearer {token2}"}
    resp = await client.get(f"/api/plans/{plan['id']}", headers=headers2)
    assert resp.status_code == 403
