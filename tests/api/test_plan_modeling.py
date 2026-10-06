import csv
import io
from decimal import Decimal

import pytest

MORTGAGE = {
    "name": "Thirty-year fixed",
    "loan_type": "mortgage",
    "currency": "eur",
    "amount": "360000",
    "interest_rate": "6",
    "term": {"years": 30},
    "start_date": "2026-01-01",
    "housing_costs": {
        "property_value": "400000",
        "property_tax_annual": "4800",
        "insurance_annual": "1200",
        "hoa_monthly": "25",
        "pmi_annual_rate": "0.5",
    },
}


async def create(client, headers, **overrides):
    response = await client.post("/api/plans", json={**MORTGAGE, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_create_mortgage_with_housing_costs(client, auth_headers):
    plan = await create(client, auth_headers)

    assert plan["loan_type"] == "mortgage"
    assert plan["currency"] == "EUR"
    assert plan["down_payment"] == "40000"
    assert plan["ltv"] == "90.00"
    assert plan["monthly_payment"] == "2158.38"
    assert plan["monthly_housing"] == {
        "property_tax": "400.00",
        "insurance": "100.00",
        "hoa": "25.00",
        "pmi": "150.00",
        "total": "675.00",
    }
    assert plan["housing_costs"]["pmi_cancel_ltv"] == "78"


@pytest.mark.anyio
async def test_new_plans_default_to_profile_currency(client, auth_headers):
    plain = {key: value for key, value in MORTGAGE.items() if key not in {"currency", "housing_costs", "loan_type"}}
    first = await client.post("/api/plans", json=plain, headers=auth_headers)
    assert first.json()["currency"] == "USD"
    assert first.json()["loan_type"] == "other"
    assert first.json()["monthly_housing"] is None

    await client.put("/api/users/me/profile", json={"currency": "CHF"}, headers=auth_headers)
    second = await client.post("/api/plans", json=plain, headers=auth_headers)
    assert second.json()["currency"] == "CHF"


@pytest.mark.anyio
async def test_invalid_housing_costs_are_rejected(client, auth_headers):
    response = await client.post(
        "/api/plans",
        json={**MORTGAGE, "housing_costs": {"pmi_annual_rate": "0.5"}},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "housing_costs.property_value"

    bad_currency = await client.post("/api/plans", json={**MORTGAGE, "currency": "E1R"}, headers=auth_headers)
    assert bad_currency.status_code == 422


@pytest.mark.anyio
async def test_update_plan_loan_details(client, auth_headers):
    plan = await create(client, auth_headers)
    response = await client.patch(
        f"/api/plans/{plan['id']}",
        json={"name": "Renamed offer", "currency": "gbp", "loan_type": "auto", "housing_costs": {}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "renamed-offer"
    assert body["currency"] == "GBP"
    assert body["loan_type"] == "auto"
    assert body["monthly_housing"] is None
    assert body["down_payment"] is None


@pytest.mark.anyio
async def test_create_with_adjustments_and_replace_them(client, auth_headers):
    plan = await create(
        client,
        auth_headers,
        interest_rate_changes=[
            {"effective_date": "2033-01-01", "rate": "7.5"},
            {"effective_date": "2031-01-01", "rate": "7"},
        ],
        recurring_extra_payments=[{"start_date": "2026-03-01", "amount": "100", "count": 12}],
    )
    assert [change["effective_date"] for change in plan["interest_rate_changes"]] == ["2031-01-01", "2033-01-01"]
    assert plan["recurring_extra_payments"][0]["amount"] == "100"

    replaced = await client.put(
        f"/api/plans/{plan['id']}/adjustments",
        json={
            "one_time_extra_payments": [{"date": "2027-06-01", "amount": "5000"}],
            "recurring_extra_payments": [],
            "interest_rate_changes": [{"effective_date": "2031-01-01", "rate": "6.5"}],
        },
        headers=auth_headers,
    )
    assert replaced.status_code == 200
    body = replaced.json()
    assert body["one_time_extra_payments"] == [{"date": "2027-06-01", "amount": "5000"}]
    assert body["recurring_extra_payments"] == []
    assert body["interest_rate_changes"] == [{"effective_date": "2031-01-01", "rate": "6.5"}]

    invalid = await client.put(
        f"/api/plans/{plan['id']}/adjustments",
        json={"one_time_extra_payments": [{"date": "2027-06-01", "amount": "-1"}]},
        headers=auth_headers,
    )
    assert invalid.status_code == 422


@pytest.mark.anyio
async def test_stored_recurring_extra_payments_generate_schedules(client, auth_headers):
    recurring = [{"start_date": "2026-02-01", "amount": "500", "count": 24}]
    plan = await create(client, auth_headers, recurring_extra_payments=recurring)

    response = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    assert response.status_code == 201
    kinds = {item["type"] for item in response.json()["installments"]}
    assert "recurring_extra" in kinds


@pytest.mark.anyio
async def test_schedule_includes_housing_and_pmi_totals(client, auth_headers):
    plan = await create(client, auth_headers)
    response = await client.post(f"/api/plans/{plan['id']}/schedules", headers=auth_headers)
    assert response.status_code == 201
    body = response.json()

    first = body["installments"][0]
    assert first["housing"]["pmi"] == "150.00"
    assert first["total_with_housing"] == "2833.38"
    assert body["totals"]["pmi"] == "15450.00"
    assert body["totals"]["escrow"] == "189000.00"

    stored = await client.get(f"/api/plans/{plan['id']}/schedules/{body['id']}", headers=auth_headers)
    assert stored.json()["installments"][0]["housing"] == first["housing"]
    assert stored.json()["totals"]["pmi"] == "15450.00"


@pytest.mark.anyio
async def test_duplicate_plan(client, auth_headers):
    plan = await create(client, auth_headers, one_time_extra_payments=[{"date": "2027-01-01", "amount": "1000"}])
    response = await client.post(f"/api/plans/{plan['id']}/duplicate", headers=auth_headers)
    assert response.status_code == 201
    copy = response.json()
    assert copy["id"] != plan["id"]
    assert copy["name"] == "Thirty-year fixed (copy)"
    assert copy["status"] == "draft"
    assert Decimal(copy["amount"]) == Decimal(plan["amount"])
    assert copy["currency"] == plan["currency"]
    assert copy["loan_type"] == plan["loan_type"]
    assert copy["monthly_housing"] == plan["monthly_housing"]
    assert copy["one_time_extra_payments"] == plan["one_time_extra_payments"]

    plans = await client.get("/api/plans", headers=auth_headers)
    assert len(plans.json()) == 2


@pytest.mark.anyio
async def test_duplicate_and_export_require_ownership(client, auth_headers, register_user):
    plan = await create(client, auth_headers)
    other_token = await register_user(client, "other@example.com")
    other = {"Authorization": f"Bearer {other_token}"}

    assert (await client.post(f"/api/plans/{plan['id']}/duplicate", headers=other)).status_code == 403
    assert (await client.get(f"/api/plans/{plan['id']}/schedule.csv", headers=other)).status_code == 403
    assert (await client.put(f"/api/plans/{plan['id']}/adjustments", json={}, headers=other)).status_code == 403


@pytest.mark.anyio
async def test_schedule_csv_export(client, auth_headers):
    plan = await create(client, auth_headers, one_time_extra_payments=[{"date": "2026-01-15", "amount": "1000"}])
    response = await client.get(f"/api/plans/{plan['id']}/schedule.csv", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="thirty-year-fixed-schedule.csv"' in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]["type"] == "one_time_extra"
    assert rows[0]["installment"] == ""
    scheduled = rows[1]
    assert scheduled["installment"] == "1"
    assert scheduled["period"] == "2026-01"
    assert scheduled["property_tax"] == "400.00"
    assert scheduled["pmi"] == "150.00"
    assert scheduled["total_payment"] == "2833.38"
