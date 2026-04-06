import pytest


@pytest.mark.asyncio
async def test_create_plan(client, auth_headers):
    resp = await client.post(
        "/api/plans",
        json={
            "name": "My Mortgage",
            "amount": "200000",
            "interest_rate": "5.5",
            "term": {"years": 30, "months": 0},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Mortgage"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_plans(client, auth_headers):
    await client.post(
        "/api/plans",
        json={"name": "Plan 1", "amount": "100000", "interest_rate": "4.0", "term": {"years": 15}},
        headers=auth_headers,
    )
    resp = await client.get("/api/plans", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_plan(client, auth_headers):
    create_resp = await client.post(
        "/api/plans",
        json={"name": "Get Plan Test", "amount": "50000", "interest_rate": "3.5", "term": {"years": 10}},
        headers=auth_headers,
    )
    plan_id = create_resp.json()["id"]
    resp = await client.get(f"/api/plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == plan_id


@pytest.mark.asyncio
async def test_delete_plan(client, auth_headers):
    create_resp = await client.post(
        "/api/plans",
        json={"name": "Delete Me", "amount": "10000", "interest_rate": "5.0", "term": {"years": 5}},
        headers=auth_headers,
    )
    plan_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 204
