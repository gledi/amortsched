import pytest


@pytest.mark.anyio
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


@pytest.mark.anyio
async def test_create_plan_includes_offer_fields(client, auth_headers):
    response = await client.post(
        "/api/plans",
        json={
            "name": "Thirty-year fixed",
            "lender": "  Bank Alpha  ",
            "upfront_fees": "1250.00",
            "amount": "300000",
            "interest_rate": "5.75",
            "term": {"years": 30, "months": 0},
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["lender"] == "Bank Alpha"
    assert response.json()["upfront_fees"] == "1250.00"


@pytest.mark.anyio
async def test_update_plan_clears_blank_lender_and_rejects_negative_upfront_fees(client, auth_headers):
    created = await client.post(
        "/api/plans",
        json={
            "name": "Offer",
            "lender": "Bank Alpha",
            "amount": "100000",
            "interest_rate": "4.5",
            "term": {"years": 15},
        },
        headers=auth_headers,
    )
    plan_id = created.json()["id"]

    cleared = await client.patch(
        f"/api/plans/{plan_id}",
        json={"lender": "   ", "upfront_fees": "900.00"},
        headers=auth_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["lender"] is None
    assert cleared.json()["upfront_fees"] == "900.00"

    rejected = await client.patch(f"/api/plans/{plan_id}", json={"upfront_fees": "-0.01"}, headers=auth_headers)
    assert rejected.status_code == 422


@pytest.mark.anyio
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


@pytest.mark.anyio
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


@pytest.mark.anyio
async def test_delete_plan(client, auth_headers):
    create_resp = await client.post(
        "/api/plans",
        json={"name": "Delete Me", "amount": "10000", "interest_rate": "5.0", "term": {"years": 5}},
        headers=auth_headers,
    )
    plan_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.get(f"/api/plans/{plan_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_rejects_empty_term_and_accepts_zero_interest(client, auth_headers):
    invalid = await client.post(
        "/api/plans",
        json={"name": "Invalid", "amount": "1000", "interest_rate": "0", "term": {}},
        headers=auth_headers,
    )
    assert invalid.status_code == 422

    valid = await client.post(
        "/api/plans",
        json={"name": "Zero interest", "amount": "1000", "interest_rate": "0", "term": {"years": 1}},
        headers=auth_headers,
    )
    assert valid.status_code == 201


@pytest.mark.anyio
async def test_create_plan_rejects_sub_cent_amount(client, auth_headers):
    response = await client.post(
        "/api/plans",
        json={
            "name": "Sub-cent",
            "amount": "200000.005",
            "interest_rate": "5.5",
            "term": {"years": 30, "months": 0},
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
