import pytest


@pytest.mark.anyio
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
    assert data["totals"]["paid_off"] is True

    listed = await client.get(f"/api/plans/{plan_id}/schedules", headers=auth_headers)
    assert [item["id"] for item in listed.json()] == [data["id"]]

    saved = await client.post(f"/api/plans/{plan_id}/schedules/{data['id']}/save", headers=auth_headers)
    assert saved.status_code == 200
    assert saved.json()["id"] == data["id"]


@pytest.mark.anyio
async def test_schedule_must_belong_to_plan_in_url(client, auth_headers):
    plan_ids = []
    for name in ("First", "Second"):
        response = await client.post(
            "/api/plans",
            json={"name": name, "amount": "1000", "interest_rate": "5", "term": {"years": 1}},
            headers=auth_headers,
        )
        plan_ids.append(response.json()["id"])

    generated = await client.post(f"/api/plans/{plan_ids[0]}/schedules", headers=auth_headers)
    schedule_id = generated.json()["id"]
    response = await client.get(f"/api/plans/{plan_ids[1]}/schedules/{schedule_id}", headers=auth_headers)
    assert response.status_code == 404
