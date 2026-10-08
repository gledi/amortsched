from decimal import Decimal

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


@pytest.mark.anyio
async def test_schedule_for_plan_with_rate_changes_pays_off_at_plan_payment(client, auth_headers):
    create_resp = await client.post(
        "/api/plans",
        json={
            "name": "Variable Plan",
            "amount": "100000",
            "interest_rate": "5",
            "term": {"years": 30},
            "start_date": "2025-01-01",
            "interest_rate_changes": [
                {"effective_date": "2025-01-01", "rate": "9"},
                {"effective_date": "2026-01-01", "rate": "12"},
            ],
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    plan = create_resp.json()

    resp = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    scheduled = [row for row in data["installments"] if row["installment_number"] is not None]

    assert data["totals"]["paid_off"] is True
    assert data["totals"]["months"] == 360
    assert Decimal(scheduled[-1]["balance"]["after"]) == 0
    assert plan["monthly_payment"] == "804.62"
    assert Decimal(scheduled[0]["total"]) == Decimal(plan["monthly_payment"])
    assert Decimal(scheduled[12]["total"]) == Decimal("1025.31")
    for row in data["installments"]:
        amounts = [row[key] for key in ("principal", "interest", "fees", "total")]
        amounts += [row["balance"]["before"], row["balance"]["after"]]
        assert all(Decimal(amount) == Decimal(amount).quantize(Decimal("0.01")) for amount in amounts), row
