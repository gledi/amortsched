"""Schedule endpoint tests for Starlette API."""

import orjson
import pytest

pytestmark = pytest.mark.anyio

PLAN_PAYLOAD = orjson.dumps(
    {
        "name": "Schedule Test Plan",
        "amount": "50000",
        "interestRate": "4.0",
        "term": {"years": 5, "months": 0},
        "startDate": "2026-01-15",
    }
)


async def _create_plan(client, headers):
    resp = await client.post("/api/plans", content=PLAN_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_preview_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(f"/api/plans/{plan['id']}/schedules/preview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["installments"]) > 0
    assert data["totals"] is not None


async def test_save_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["planId"] == plan["id"]


async def test_list_schedules(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    resp = await client.get(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_get_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    save_resp = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    schedule_id = save_resp.json()["id"]
    resp = await client.get(f"/api/plans/{plan['id']}/schedules/{schedule_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == schedule_id


async def test_delete_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    save_resp = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    schedule_id = save_resp.json()["id"]
    resp = await client.delete(f"/api/plans/{plan['id']}/schedules/{schedule_id}", headers=auth_headers)
    assert resp.status_code == 204
