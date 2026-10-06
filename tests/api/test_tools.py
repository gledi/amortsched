from decimal import Decimal

import pytest


@pytest.mark.anyio
async def test_tools_require_authentication(client):
    response = await client.post("/api/tools/affordability", json={"gross_monthly_income": "1", "interest_rate": "1"})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_affordability(client, auth_headers):
    response = await client.post(
        "/api/tools/affordability",
        json={
            "gross_monthly_income": "10000",
            "monthly_debts": "500",
            "down_payment": "60000",
            "interest_rate": "6.5",
            "property_tax_rate": "1.1",
            "insurance_annual": "1500",
            "pmi_annual_rate": "0.5",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["limiting_ratio"] == "front_end"
    assert body["max_monthly_housing"] == "2800.00"
    assert Decimal(body["monthly"]["total"]) <= Decimal("2800")
    assert Decimal(body["max_home_price"]) - Decimal(body["max_loan_amount"]) == Decimal("60000")
    assert Decimal(body["monthly"]["pmi"]) > 0


@pytest.mark.anyio
async def test_refinance_manual_inputs(client, auth_headers):
    response = await client.post(
        "/api/tools/refinance",
        json={
            "current_balance": "300000",
            "current_rate": "7",
            "remaining_months": 300,
            "new_rate": "5.5",
            "new_term_months": 300,
            "closing_costs": "6000",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_loan"] == {"balance": "300000", "rate": "7", "remaining_months": 300, "currency": None}
    assert body["break_even_month"] == 17
    assert body["advantage_by_month"][0] == "-6000.00"
    assert len(body["advantage_by_month"]) == 301


@pytest.mark.anyio
async def test_refinance_requires_a_loan_source(client, auth_headers):
    response = await client.post(
        "/api/tools/refinance",
        json={"new_rate": "5", "new_term_months": 360},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_refinance_from_plan_uses_balance_and_rate_on_date(client, auth_headers):
    created = await client.post(
        "/api/plans",
        json={
            "name": "Home",
            "currency": "EUR",
            "amount": "1200",
            "interest_rate": "0",
            "term": {"years": 1},
            "start_date": "2026-01-01",
            "interest_rate_changes": [{"effective_date": "2026-03-01", "rate": "6"}],
        },
        headers=auth_headers,
    )
    plan_id = created.json()["id"]

    response = await client.post(
        "/api/tools/refinance",
        json={"plan_id": plan_id, "as_of": "2026-07-01", "new_rate": "3", "new_term_months": 6},
        headers=auth_headers,
    )
    assert response.status_code == 200
    current = response.json()["current_loan"]
    assert current["currency"] == "EUR"
    assert current["rate"] == "6"
    assert current["remaining_months"] == 6
    assert Decimal(current["balance"]) < Decimal("1200")

    paid_off = await client.post(
        "/api/tools/refinance",
        json={"plan_id": plan_id, "as_of": "2030-01-01", "new_rate": "3", "new_term_months": 6},
        headers=auth_headers,
    )
    assert paid_off.status_code == 422


@pytest.mark.anyio
async def test_plan_based_tools_enforce_ownership(client, auth_headers, register_user):
    created = await client.post(
        "/api/plans",
        json={"name": "Home", "amount": "1200", "interest_rate": "1", "term": {"years": 1}},
        headers=auth_headers,
    )
    plan_id = created.json()["id"]
    other = {"Authorization": f"Bearer {await register_user(client, 'other@example.com')}"}

    refinance = await client.post(
        "/api/tools/refinance",
        json={"plan_id": plan_id, "new_rate": "1", "new_term_months": 12},
        headers=other,
    )
    prepay = await client.post(
        "/api/tools/prepay-vs-invest",
        json={"plan_id": plan_id, "extra_monthly": "10", "annual_return": "5"},
        headers=other,
    )
    assert refinance.status_code == 403
    assert prepay.status_code == 403


@pytest.mark.anyio
async def test_prepay_vs_invest_from_plan(client, auth_headers):
    created = await client.post(
        "/api/plans",
        json={"name": "Home", "amount": "200000", "interest_rate": "6", "term": {"years": 30}, "currency": "GBP"},
        headers=auth_headers,
    )
    response = await client.post(
        "/api/tools/prepay-vs-invest",
        json={"plan_id": created.json()["id"], "extra_monthly": "300", "annual_return": "9"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["loan"] == {
        "principal": "200000.00",
        "interest_rate": "6.000000",
        "term_months": 360,
        "currency": "GBP",
    }
    assert body["better_strategy"] == "invest"
    assert body["break_even_return"] == "6.00"
    assert len(body["timeline"]) == 360
    assert body["months_saved"] > 0
