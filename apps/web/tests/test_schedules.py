"""Schedule endpoint tests for FastAPI web app."""

import pytest

pytestmark = pytest.mark.anyio

PLAN_DATA = {
    "name": "Schedule Plan",
    "amount": "50000",
    "interestRate": "4.0",
    "term": {"years": 5, "months": 0},
    "startDate": "2026-01-15",
}


async def _create_plan(client, headers):
    resp = await client.post("/api/plans", json=PLAN_DATA, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_preview_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(f"/api/plans/{plan['id']}/schedules/preview", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["installments"]) > 0


async def test_save_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    resp = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    assert resp.status_code == 201
    assert "id" in resp.json()


async def test_list_schedules(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    resp = await client.get(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_get_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    save_resp = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    sid = save_resp.json()["id"]
    resp = await client.get(f"/api/plans/{plan['id']}/schedules/{sid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_delete_schedule(client, auth_headers):
    plan = await _create_plan(client, auth_headers)
    save_resp = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    sid = save_resp.json()["id"]
    resp = await client.delete(f"/api/plans/{plan['id']}/schedules/{sid}", headers=auth_headers)
    assert resp.status_code == 204
