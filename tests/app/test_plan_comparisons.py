import datetime
import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Never, cast

import pytest

from amortsched.app.queries.comparisons import ComparePlansHandler, ComparePlansQuery
from amortsched.core.entities import Plan, Schedule
from amortsched.core.errors import PlanNotFoundError, ValidationError
from amortsched.core.pagination import Paginated, Pagination
from amortsched.core.specifications import Specification
from amortsched.core.values import (
    Balance,
    EarlyPaymentFees,
    Installment,
    InterestRateChange,
    Month,
    OneTimeExtraPayment,
    Payment,
    PaymentKind,
    RecurringExtraPayment,
    ScheduleTotals,
    Term,
)

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


class ReadOnlyPlanRepo:
    def __init__(self, plans: list[Plan]) -> None:
        self._plans = plans
        self.get_items_calls = 0
        self.write_calls = 0

    async def get_by_id(self, id: uuid.UUID, specification: Specification[Plan] | None = None) -> Plan | None:
        for plan in self._plans:
            if plan.id == id and (specification is None or specification(plan)):
                return plan
        return None

    async def get_one(self, specification: Specification[Plan]) -> Plan:
        return next(plan for plan in self._plans if specification(plan))

    async def get_one_or_none(self, specification: Specification[Plan]) -> Plan | None:
        return next((plan for plan in self._plans if specification(plan)), None)

    async def get_paginated(
        self,
        specification: Specification[Plan] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[Plan]:
        raise AssertionError("comparison must use the bounded collection read")

    async def count(self, specification: Specification[Plan] | None = None) -> int:
        raise AssertionError("comparison must use the bounded collection read")

    async def exists(self, specification: Specification[Plan]) -> bool:
        raise AssertionError("comparison must use the bounded collection read")

    def get_items(
        self,
        specification: Specification[Plan] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Plan]:
        self.get_items_calls += 1

        async def items() -> AsyncIterator[Plan]:
            matched = [plan for plan in self._plans if specification is None or specification(plan)]
            for plan in matched[:limit]:
                yield plan

        return items()

    async def add(self, item: Plan) -> Never:
        self.write_calls += 1
        raise AssertionError("comparison must not persist")

    async def update(self, item: Plan) -> Never:
        self.write_calls += 1
        raise AssertionError("comparison must not persist")

    async def save(self, item: Plan, conflict_on: Sequence[str] = ("id",)) -> Never:
        self.write_calls += 1
        raise AssertionError("comparison must not persist")

    async def delete(self, specification: Specification[Plan]) -> Never:
        self.write_calls += 1
        raise AssertionError("comparison must not persist")

    async def purge(self, specification: Specification[Plan]) -> Never:
        self.write_calls += 1
        raise AssertionError("comparison must not persist")


class UnpaidPlan(Plan):
    __slots__ = ()

    def generate(self) -> Schedule:
        return Schedule(
            plan_id=self.id,
            installments=[
                Installment(
                    i=1,
                    year=2026,
                    month=Month.January,
                    payment=Payment(
                        kind=PaymentKind.ScheduledPayment,
                        principal=Decimal("100.00"),
                        interest=Decimal("0.00"),
                        fees=Decimal("0.00"),
                    ),
                    balance=Balance(before=self.amount, after=self.amount - Decimal("100.00")),
                )
            ],
            totals=ScheduleTotals(
                principal=Decimal("100.00"),
                interest=Decimal("0.00"),
                fees=Decimal("0.00"),
                months=1,
                paid_off=False,
            ),
        )


class InvalidSchedulePlan(Plan):
    __slots__ = ()

    def generate(self) -> Schedule:
        return Schedule(plan_id=self.id, installments=[], totals=None)


def make_plan(
    *,
    name: str,
    amount: str = "1200",
    interest_rate: str = "0",
    upfront_fees: str = "0",
    user_id: uuid.UUID = USER_ID,
    plan_type: type[Plan] = Plan,
    one_time_extra_payments: list[OneTimeExtraPayment] | None = None,
    recurring_extra_payments: list[RecurringExtraPayment] | None = None,
    interest_rate_changes: list[InterestRateChange] | None = None,
) -> Plan:
    return plan_type(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, f"{user_id}-{name}"),
        user_id=user_id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        amount=Decimal(amount),
        term=Term(1),
        interest_rate=Decimal(interest_rate),
        start_date=datetime.date(2026, 1, 1),
        lender="Lender",
        upfront_fees=Decimal(upfront_fees),
        early_payment_fees=EarlyPaymentFees(fixed=Decimal("2.00"), percent=Decimal("1.00")),
        one_time_extra_payments=one_time_extra_payments or [],
        recurring_extra_payments=recurring_extra_payments or [],
        interest_rate_changes=interest_rate_changes or [],
    )


@pytest.mark.anyio
async def test_compare_plans_preserves_order_and_never_persists():
    first = make_plan(name="Alpha", amount="1200", upfront_fees="100")
    second = make_plan(name="Beta", amount="1200", upfront_fees="20")
    repo = ReadOnlyPlanRepo([first, second])

    result = await ComparePlansHandler(repo).handle(
        ComparePlansQuery(plan_ids=(second.id, first.id), user_id=first.user_id)
    )

    assert [item.id for item in result.plans] == [second.id, first.id]
    assert result.overall_winner_plan_ids == (second.id,)
    assert result.savings_vs_next_best == Decimal("80.00")
    assert repo.get_items_calls == 1
    assert repo.write_calls == 0


@pytest.mark.anyio
@pytest.mark.parametrize("count", [1, 5])
async def test_compare_plans_rejects_selection_outside_two_to_four(count: int):
    plans = [make_plan(name=f"Plan {index}") for index in range(count)]

    with pytest.raises(ValidationError):
        await ComparePlansHandler(ReadOnlyPlanRepo(plans)).handle(
            ComparePlansQuery(plan_ids=tuple(plan.id for plan in plans), user_id=plans[0].user_id)
        )


@pytest.mark.anyio
async def test_compare_plans_rejects_duplicates():
    plan = make_plan(name="Duplicate")

    with pytest.raises(ValidationError):
        await ComparePlansHandler(ReadOnlyPlanRepo([plan])).handle(
            ComparePlansQuery(plan_ids=(plan.id, plan.id), user_id=plan.user_id)
        )


@pytest.mark.anyio
async def test_compare_plans_rejects_missing_or_not_owned_selection():
    owned = make_plan(name="Owned")
    unowned = make_plan(name="Unowned", user_id=OTHER_USER_ID)
    repo = ReadOnlyPlanRepo([owned, unowned])

    with pytest.raises(PlanNotFoundError) as exception:
        await ComparePlansHandler(repo).handle(
            ComparePlansQuery(plan_ids=(owned.id, unowned.id), user_id=owned.user_id)
        )

    assert exception.value.plan_id == "comparison selection"
    assert repo.get_items_calls == 1
    assert repo.write_calls == 0


@pytest.mark.anyio
async def test_compare_plans_marks_different_principals_incomparable():
    lower = make_plan(name="Lower", amount="1000")
    higher = make_plan(name="Higher", amount="1200")

    result = await ComparePlansHandler(ReadOnlyPlanRepo([lower, higher])).handle(
        ComparePlansQuery(plan_ids=(lower.id, higher.id), user_id=lower.user_id)
    )

    assert result.directly_comparable is False
    assert result.incomparability_reasons == ("Principal amounts differ",)
    assert result.overall_winner_plan_ids == ()
    assert result.savings_vs_next_best is None


@pytest.mark.anyio
async def test_compare_plans_marks_unpaid_schedules_incomparable():
    paid = make_plan(name="Paid")
    unpaid = make_plan(name="Unpaid", plan_type=UnpaidPlan)

    result = await ComparePlansHandler(ReadOnlyPlanRepo([paid, unpaid])).handle(
        ComparePlansQuery(plan_ids=(paid.id, unpaid.id), user_id=paid.user_id)
    )

    assert result.directly_comparable is False
    assert result.incomparability_reasons == ("One or more schedules did not pay off",)
    assert result.overall_winner_plan_ids == ()
    assert result.savings_vs_next_best is None


@pytest.mark.anyio
async def test_compare_plans_rejects_invalid_generated_schedule():
    valid = make_plan(name="Valid")
    invalid = make_plan(name="Invalid", plan_type=InvalidSchedulePlan)

    with pytest.raises(ValidationError) as exception:
        await ComparePlansHandler(ReadOnlyPlanRepo([valid, invalid])).handle(
            ComparePlansQuery(plan_ids=(valid.id, invalid.id), user_id=valid.user_id)
        )

    assert exception.value.errors == [
        {"field": "plan_ids", "message": "A selected plan could not produce comparison totals"}
    ]


@pytest.mark.anyio
async def test_compare_plans_retains_tied_overall_winners():
    first = make_plan(name="First", upfront_fees="20")
    second = make_plan(name="Second", upfront_fees="20")

    result = await ComparePlansHandler(ReadOnlyPlanRepo([first, second])).handle(
        ComparePlansQuery(plan_ids=(first.id, second.id), user_id=first.user_id)
    )

    assert result.directly_comparable is True
    assert result.overall_winner_plan_ids == (first.id, second.id)
    assert result.savings_vs_next_best is None


@pytest.mark.anyio
async def test_compare_plans_retains_tied_metric_winners():
    first = make_plan(name="First", interest_rate="3", upfront_fees="50")
    second = make_plan(name="Second", interest_rate="3", upfront_fees="10")

    result = await ComparePlansHandler(ReadOnlyPlanRepo([first, second])).handle(
        ComparePlansQuery(plan_ids=(first.id, second.id), user_id=first.user_id)
    )

    assert result.best_plan_ids_by_metric["interest_rate"] == (first.id, second.id)
    assert result.best_plan_ids_by_metric["upfront_fees"] == (second.id,)
    assert result.best_plan_ids_by_metric["total_cost"] == (second.id,)


@pytest.mark.anyio
async def test_compare_plans_uses_first_scheduled_payment_and_last_installment_for_payoff():
    adjusted = make_plan(
        name="Adjusted",
        one_time_extra_payments=[OneTimeExtraPayment(date=datetime.date(2026, 1, 15), amount=Decimal("100.00"))],
        recurring_extra_payments=[
            RecurringExtraPayment(start_date=datetime.date(2026, 2, 15), amount=Decimal("10.00"), count=1)
        ],
        interest_rate_changes=[
            InterestRateChange(effective_date=datetime.date(2026, 3, 1), yearly_interest_rate=Decimal("0"))
        ],
    )
    standard = make_plan(name="Standard")

    result = await ComparePlansHandler(ReadOnlyPlanRepo([adjusted, standard])).handle(
        ComparePlansQuery(plan_ids=(adjusted.id, standard.id), user_id=adjusted.user_id)
    )
    item = result.plans[0]

    assert item.starting_monthly_payment == Decimal("100.00")
    assert item.payoff_month == "2026-11"
    assert item.adjustment_counts.one_time_extra_payments == 1
    assert item.adjustment_counts.recurring_extra_payments == 1
    assert item.adjustment_counts.interest_rate_changes == 1
    assert item.configured_early_payment_fees == adjusted.early_payment_fees


@pytest.mark.anyio
async def test_compare_plans_exposes_hand_derived_cost_totals():
    first = make_plan(name="Alpha", amount="1200", upfront_fees="25")
    second = make_plan(name="Beta", amount="1200", upfront_fees="75")

    result = await ComparePlansHandler(ReadOnlyPlanRepo([first, second])).handle(
        ComparePlansQuery(plan_ids=(first.id, second.id), user_id=first.user_id)
    )
    item = result.plans[0]

    assert item.principal == Decimal("1200")
    assert item.total_principal == Decimal("1200")
    assert item.total_interest == Decimal("0.00")
    assert item.schedule_fees == Decimal("0.00")
    assert item.schedule_total_outflow == Decimal("1200.00")
    assert item.total_cost == Decimal("1225.00")
    assert item.payoff_month == "2026-12"


@pytest.mark.anyio
async def test_compare_plans_rejects_metric_mapping_mutation():
    first = make_plan(name="First")
    second = make_plan(name="Second")

    result = await ComparePlansHandler(ReadOnlyPlanRepo([first, second])).handle(
        ComparePlansQuery(plan_ids=(first.id, second.id), user_id=first.user_id)
    )

    with pytest.raises(TypeError):
        cast(dict[str, tuple[uuid.UUID, ...]], result.best_plan_ids_by_metric)["total_cost"] = ()


@pytest.mark.anyio
async def test_compare_plans_returns_immutable_term_and_fee_snapshots():
    first = make_plan(name="First")
    second = make_plan(name="Second")

    result = await ComparePlansHandler(ReadOnlyPlanRepo([first, second])).handle(
        ComparePlansQuery(plan_ids=(first.id, second.id), user_id=first.user_id)
    )
    item = result.plans[0]

    assert item.term is not first.term
    assert item.configured_early_payment_fees is not first.early_payment_fees
    with pytest.raises(FrozenInstanceError):
        item.term.years = 2  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(FrozenInstanceError):
        item.configured_early_payment_fees.fixed = Decimal("9.00")  # pyright: ignore[reportAttributeAccessIssue]
    assert first.term.years == 1
    assert first.early_payment_fees.fixed == Decimal("2.00")
