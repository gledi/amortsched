import datetime
import uuid
from decimal import Decimal

import pytest

from amortsched.api.dependencies import get_plan_repo
from amortsched.core.entities import Plan, Schedule
from amortsched.core.values import Term


class InvalidSchedulePlan(Plan):
    __slots__ = ()

    def generate(self) -> Schedule:
        return Schedule(plan_id=self.id, installments=[], totals=None)


class ComparisonPlanRepo:
    def __init__(self, plans: list[Plan]) -> None:
        self._plans = plans

    def get_items(self, *_args, **_kwargs):
        async def items():
            for plan in self._plans:
                yield plan

        return items()


async def create_offer(client, auth_headers, name: str, upfront_fees: str, amount: str = "1200") -> str:
    response = await client.post(
        "/api/plans",
        json={
            "name": name,
            "amount": amount,
            "interest_rate": "0",
            "term": {"years": 1},
            "upfront_fees": upfront_fees,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.anyio
async def test_preview_compares_plans_without_saving_schedules(client, auth_headers):
    first_id = await create_offer(client, auth_headers, "Alpha", "100")
    second_id = await create_offer(client, auth_headers, "Beta", "20")

    response = await client.post(
        "/api/plan-comparisons/preview",
        json={"plan_ids": [second_id, first_id]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["plans"]] == [second_id, first_id]
    assert body["overall_winner_plan_ids"] == [second_id]
    assert body["plans"][0]["total_cost"] == "1220.00"
    assert body["plans"][0]["payoff_months"] == 12

    for plan_id in (first_id, second_id):
        schedules = await client.get(f"/api/plans/{plan_id}/schedules", headers=auth_headers)
        assert schedules.json() == []


@pytest.mark.anyio
async def test_preview_accepts_four_plans_and_preserves_order(client, auth_headers):
    plan_ids = [await create_offer(client, auth_headers, f"Offer {index}", str(index)) for index in range(4)]

    response = await client.post(
        "/api/plan-comparisons/preview",
        json={"plan_ids": plan_ids[::-1]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["plans"]] == plan_ids[::-1]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "plan_ids",
    [
        [str(uuid.uuid4())],
        [str(uuid.uuid4()) for _ in range(5)],
        ["00000000-0000-0000-0000-000000000001"] * 2,
        ["not-a-uuid", "00000000-0000-0000-0000-000000000001"],
    ],
)
async def test_preview_rejects_invalid_selection_shape(client, auth_headers, plan_ids):
    response = await client.post(
        "/api/plan-comparisons/preview",
        json={"plan_ids": plan_ids},
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_preview_marks_different_principals_incomparable(client, auth_headers):
    lower_id = await create_offer(client, auth_headers, "Lower", "0", amount="1000")
    higher_id = await create_offer(client, auth_headers, "Higher", "0", amount="1200")

    response = await client.post(
        "/api/plan-comparisons/preview",
        json={"plan_ids": [lower_id, higher_id]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["directly_comparable"] is False
    assert body["incomparability_reasons"] == ["Principal amounts differ"]
    assert body["overall_winner_plan_ids"] == []
    assert body["savings_vs_next_best"] is None


@pytest.mark.anyio
async def test_preview_hides_another_users_plan_ownership(client, auth_headers, register_user):
    owned_id = await create_offer(client, auth_headers, "Owned", "0")
    other_token = await register_user(client, "other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    unowned_id = await create_offer(client, other_headers, "Unowned", "0")

    response = await client.post(
        "/api/plan-comparisons/preview",
        json={"plan_ids": [owned_id, unowned_id]},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "own" not in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_preview_returns_422_when_generation_fails_without_saving_schedules(client, auth_headers):
    first_id = await create_offer(client, auth_headers, "Valid", "0")
    second_id = await create_offer(client, auth_headers, "Invalid", "0")
    first_plan = await client.get(f"/api/plans/{first_id}", headers=auth_headers)
    second_plan = await client.get(f"/api/plans/{second_id}", headers=auth_headers)

    valid = Plan(
        id=uuid.UUID(first_plan.json()["id"]),
        user_id=uuid.UUID(first_plan.json()["user_id"]),
        name="Valid",
        slug="valid",
        amount=Decimal("1200"),
        term=Term(1),
        interest_rate=Decimal("0"),
        start_date=datetime.date(2026, 1, 1),
    )
    invalid = InvalidSchedulePlan(
        id=uuid.UUID(second_plan.json()["id"]),
        user_id=uuid.UUID(second_plan.json()["user_id"]),
        name="Invalid",
        slug="invalid",
        amount=Decimal("1200"),
        term=Term(1),
        interest_rate=Decimal("0"),
        start_date=datetime.date(2026, 1, 1),
    )
    app = client._transport.app
    app.dependency_overrides[get_plan_repo] = lambda: ComparisonPlanRepo([valid, invalid])
    try:
        response = await client.post(
            "/api/plan-comparisons/preview",
            json={"plan_ids": [first_id, second_id]},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_plan_repo)

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "plan_ids", "message": "A selected plan could not produce comparison totals"}
    ]
    for plan_id in (first_id, second_id):
        schedules = await client.get(f"/api/plans/{plan_id}/schedules", headers=auth_headers)
        assert schedules.json() == []


@pytest.mark.anyio
async def test_preview_with_horizon_and_currency_details(client, auth_headers):
    first_id = await create_offer(client, auth_headers, "Alpha", "100")
    second_id = await create_offer(client, auth_headers, "Beta", "20")

    response = await client.post(
        "/api/plan-comparisons/preview",
        json={"plan_ids": [first_id, second_id], "horizon_months": 6},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["horizon_months"] == 6
    assert body["horizon_winner_plan_ids"] == [second_id]
    first = body["plans"][0]
    assert first["currency"] == "USD"
    assert first["cumulative_cost"][0] == "100.00"
    assert len(first["cumulative_cost"]) == 13
    assert first["horizon"] == {"months": 6, "cost": "100.00", "balance": "600.00", "payoff_penalty": "0.00"}
    assert first["starting_total_monthly_payment"] == "100.00"
    assert first["total_pmi"] == "0.00"


@pytest.mark.anyio
async def test_preview_rejects_out_of_range_horizon(client, auth_headers):
    first_id = await create_offer(client, auth_headers, "Alpha", "100")
    second_id = await create_offer(client, auth_headers, "Beta", "20")
    response = await client.post(
        "/api/plan-comparisons/preview",
        json={"plan_ids": [first_id, second_id], "horizon_months": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422
