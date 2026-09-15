import datetime
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from amortsched.core.entities import Plan
from amortsched.core.errors import PlanNotFoundError, ValidationError
from amortsched.core.repositories import AsyncRepository
from amortsched.core.specifications import Eq, In
from amortsched.core.values import EarlyPaymentFees, Term


@dataclass(frozen=True, slots=True)
class AdjustmentCounts:
    one_time_extra_payments: int
    recurring_extra_payments: int
    interest_rate_changes: int


@dataclass(frozen=True, slots=True)
class PlanComparisonItem:
    id: uuid.UUID
    name: str
    lender: str | None
    principal: Decimal
    interest_rate: Decimal
    term: Term
    start_date: datetime.date
    starting_monthly_payment: Decimal
    configured_early_payment_fees: EarlyPaymentFees
    upfront_fees: Decimal
    total_principal: Decimal
    total_interest: Decimal
    schedule_fees: Decimal
    schedule_total_outflow: Decimal
    total_cost: Decimal
    payoff_months: int
    payoff_month: str
    paid_off: bool
    adjustment_counts: AdjustmentCounts


@dataclass(frozen=True, slots=True)
class PlanComparison:
    directly_comparable: bool
    incomparability_reasons: tuple[str, ...]
    overall_winner_plan_ids: tuple[uuid.UUID, ...]
    savings_vs_next_best: Decimal | None
    best_plan_ids_by_metric: Mapping[str, tuple[uuid.UUID, ...]]
    plans: tuple[PlanComparisonItem, ...]


@dataclass(frozen=True, slots=True)
class ComparePlansQuery:
    plan_ids: tuple[uuid.UUID, ...]
    user_id: uuid.UUID


def _lowest_ids(
    items: tuple[PlanComparisonItem, ...], value: Callable[[PlanComparisonItem], Decimal]
) -> tuple[uuid.UUID, ...]:
    lowest = min(value(item) for item in items)
    return tuple(item.id for item in items if value(item) == lowest)


class ComparePlansHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, query: ComparePlansQuery) -> PlanComparison:
        self._validate_selection(query.plan_ids)

        specification = In("id", query.plan_ids) & Eq("user_id", query.user_id)
        found = [plan async for plan in self._plan_repo.get_items(specification)]
        plans_by_id = {plan.id: plan for plan in found}
        if len(plans_by_id) != len(query.plan_ids):
            raise PlanNotFoundError("comparison selection")
        ordered = [plans_by_id[plan_id] for plan_id in query.plan_ids]
        items = tuple(self._comparison_item(plan) for plan in ordered)

        reasons: list[str] = []
        if len({item.principal for item in items}) != 1:
            reasons.append("Principal amounts differ")
        if not all(item.paid_off for item in items):
            reasons.append("One or more schedules did not pay off")
        directly_comparable = not reasons

        best_plan_ids_by_metric = {
            "interest_rate": _lowest_ids(items, lambda item: item.interest_rate),
            "starting_monthly_payment": _lowest_ids(items, lambda item: item.starting_monthly_payment),
            "total_interest": _lowest_ids(items, lambda item: item.total_interest),
            "schedule_fees": _lowest_ids(items, lambda item: item.schedule_fees),
            "upfront_fees": _lowest_ids(items, lambda item: item.upfront_fees),
            "total_cost": _lowest_ids(items, lambda item: item.total_cost),
        }

        overall_winner_plan_ids: tuple[uuid.UUID, ...] = ()
        savings_vs_next_best: Decimal | None = None
        if directly_comparable:
            overall_winner_plan_ids = best_plan_ids_by_metric["total_cost"]
            if len(overall_winner_plan_ids) == 1:
                costs = sorted({item.total_cost for item in items})
                savings_vs_next_best = costs[1] - costs[0]

        return PlanComparison(
            directly_comparable=directly_comparable,
            incomparability_reasons=tuple(reasons),
            overall_winner_plan_ids=overall_winner_plan_ids,
            savings_vs_next_best=savings_vs_next_best,
            best_plan_ids_by_metric=MappingProxyType(best_plan_ids_by_metric),
            plans=items,
        )

    @staticmethod
    def _validate_selection(plan_ids: tuple[uuid.UUID, ...]) -> None:
        if not 2 <= len(plan_ids) <= 4:
            raise ValidationError([{"field": "plan_ids", "message": "Select between two and four plans"}])
        if len(set(plan_ids)) != len(plan_ids):
            raise ValidationError([{"field": "plan_ids", "message": "Plan selection must not contain duplicates"}])

    @staticmethod
    def _comparison_item(plan: Plan) -> PlanComparisonItem:
        schedule = plan.generate()
        first_scheduled = next((item for item in schedule.installments if item.i is not None), None)
        if schedule.totals is None or first_scheduled is None or not schedule.installments:
            raise ValidationError(
                [{"field": "plan_ids", "message": "A selected plan could not produce comparison totals"}]
            )
        totals = schedule.totals
        last_installment = schedule.installments[-1]
        schedule_total_outflow = totals.total_outflow

        return PlanComparisonItem(
            id=plan.id,
            name=plan.name,
            lender=plan.lender,
            principal=plan.amount,
            interest_rate=plan.interest_rate,
            term=Term(plan.term.years, plan.term.months),
            start_date=plan.start_date,
            starting_monthly_payment=first_scheduled.payment.total,
            configured_early_payment_fees=EarlyPaymentFees(
                fixed=plan.early_payment_fees.fixed,
                percent=plan.early_payment_fees.percent,
            ),
            upfront_fees=plan.upfront_fees,
            total_principal=totals.principal,
            total_interest=totals.interest,
            schedule_fees=totals.fees,
            schedule_total_outflow=schedule_total_outflow,
            total_cost=schedule_total_outflow + plan.upfront_fees,
            payoff_months=totals.months,
            payoff_month=f"{last_installment.year:04d}-{int(last_installment.month):02d}",
            paid_off=totals.paid_off,
            adjustment_counts=AdjustmentCounts(
                one_time_extra_payments=len(plan.one_time_extra_payments),
                recurring_extra_payments=len(plan.recurring_extra_payments),
                interest_rate_changes=len(plan.interest_rate_changes),
            ),
        )
