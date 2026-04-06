import pytest


@pytest.mark.asyncio
async def test_generate_schedule(client, auth_headers):
    create_resp = await client.post(
        "/api/plans",
        json={"name": "Schedule Plan", "amount": "100000", "interest_rate": "5.0", "term": {"years": 30}},
        headers=auth_headers,
    )
    plan_id = create_resp.json()["id"]

    resp = await client.post(f"/api/plans/{plan_id}/schedules", headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["installments"]) > 0
    assert data["totals"]["months"] == 360
