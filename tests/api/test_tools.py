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


@pytest.mark.anyio
async def test_refinance_rejects_sub_cent_current_balance(client, auth_headers):
    response = await client.post(
        "/api/tools/refinance",
        json={
            "current_balance": "300000.001",
            "current_rate": "7",
            "remaining_months": 300,
            "new_rate": "5.5",
            "new_term_months": 300,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_entered_terms_refinance_matches_a_plan_with_the_same_terms(client, auth_headers):
    created = await client.post(
        "/api/plans",
        json={
            "name": "Same terms",
            "amount": "250000",
            "interest_rate": "6.75",
            "term": {"years": 20, "months": 7},
            "start_date": "2026-01-31",
        },
        headers=auth_headers,
    )
    schedule = (await client.post(f"/api/plans/{created.json()['id']}/schedules", headers=auth_headers)).json()

    response = await client.post(
        "/api/tools/refinance",
        json={
            "as_of": "2026-01-31",
            "current_balance": "250000",
            "current_rate": "6.75",
            "remaining_months": 247,
            "new_rate": "5",
            "new_term_months": 120,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["current_payment"]) == Decimal(schedule["installments"][0]["total"])
    assert Decimal(body["current_total_interest"]) == Decimal(schedule["totals"]["interest"])
    assert Decimal(body["current_total_paid"]) == Decimal(schedule["totals"]["total_outflow"])


VARIABLE_RATE_PLAN = {
    "name": "Variable",
    "amount": "100000",
    "interest_rate": "5",
    "term": {"years": 5},
    "start_date": "2026-01-10",
    "upfront_fees": "3000",
    "interest_rate_application": "prorated_by_payment_period",
    "early_payment_fees": {"fixed": "25", "percent": "1"},
    "interest_rate_changes": [{"effective_date": "2027-01-25", "rate": "7"}],
    "one_time_extra_payments": [
        {"date": "2026-04-05", "amount": "5000"},
        {"date": "2028-03-05", "amount": "1000"},
    ],
    "recurring_extra_payments": [{"start_date": "2026-02-05", "amount": "200", "count": 24}],
}


@pytest.mark.anyio
async def test_refinance_from_plan_keeps_the_plans_own_schedule_as_the_current_loan(client, auth_headers):
    created = await client.post("/api/plans", json=VARIABLE_RATE_PLAN, headers=auth_headers)
    plan_id = created.json()["id"]
    schedule = (await client.post(f"/api/plans/{plan_id}/schedules", headers=auth_headers)).json()
    installments = schedule["installments"]
    june = next(index for index, row in enumerate(installments) if row["installment_number"] == 6)
    assert (installments[june]["year"], installments[june]["month"]) == (2026, 6)
    remaining = installments[june + 1 :]

    response = await client.post(
        "/api/tools/refinance",
        json={"plan_id": plan_id, "as_of": "2026-07-01", "new_rate": "4", "new_term_months": 48},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    scheduled = [row for row in remaining if row["installment_number"] is not None]
    assert Decimal(body["current_payment"]) == Decimal(scheduled[0]["total"])
    assert Decimal(body["current_total_interest"]) == sum(Decimal(row["interest"]) for row in remaining)
    assert Decimal(body["current_total_paid"]) == sum(Decimal(row["total"]) for row in remaining)
    assert Decimal(body["current_loan"]["balance"]) == Decimal(installments[june]["balance"]["after"])
    assert body["current_loan"]["remaining_months"] == len(scheduled)
    assert Decimal(body["current_loan"]["rate"]) == Decimal("5")


@pytest.mark.anyio
async def test_refinanced_plan_loan_keeps_future_extras_without_penalties_on_the_plans_payment_day(
    client, auth_headers
):
    created = await client.post("/api/plans", json=VARIABLE_RATE_PLAN, headers=auth_headers)
    response = await client.post(
        "/api/tools/refinance",
        json={
            "plan_id": created.json()["id"],
            "as_of": "2026-07-01",
            "new_rate": "4",
            "new_term_months": 48,
            "closing_costs": "2000",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()

    refinanced = await client.post(
        "/api/plans",
        json={
            "name": "Refinanced",
            "amount": body["new_principal"],
            "interest_rate": "4",
            "term": {"years": 4},
            "start_date": "2026-07-10",
            "interest_rate_application": "prorated_by_payment_period",
            "one_time_extra_payments": [{"date": "2028-03-05", "amount": "1000"}],
            "recurring_extra_payments": [{"start_date": "2026-08-05", "amount": "200", "count": 18}],
        },
        headers=auth_headers,
    )
    schedule = (await client.post(f"/api/plans/{refinanced.json()['id']}/schedules", headers=auth_headers)).json()
    assert Decimal(schedule["totals"]["fees"]) == 0
    scheduled = [row for row in schedule["installments"] if row["installment_number"] is not None]
    assert Decimal(body["new_payment"]) == Decimal(scheduled[0]["total"])
    assert Decimal(body["new_total_interest"]) == Decimal(schedule["totals"]["interest"])
    assert Decimal(body["new_total_paid"]) == Decimal(schedule["totals"]["total_outflow"]) + 2000
    assert body["cash_due_at_closing"] == "2000.00"
