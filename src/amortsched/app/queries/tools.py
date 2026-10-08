import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from amortsched.app.access import get_owned_plan
from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.calculators import (
    PrepayVsInvestInput,
    PrepayVsInvestResult,
    RefinanceInput,
    RefinanceResult,
    prepay_vs_invest,
    refinance,
)
from amortsched.core.entities import Plan
from amortsched.core.errors import ValidationError
from amortsched.core.repositories import AsyncRepository
from amortsched.core.values import InterestRateApplication


def entered_terms_schedule(principal: Decimal, annual_rate: Decimal, months: int) -> AmortizationSchedule:
    """A temporary schedule for loan terms entered without a plan: no extras, no fees, whole-month interest.

    Generate it from the run's start date.
    """
    return AmortizationSchedule(
        principal,
        (0, months),
        annual_rate,
        interest_rate_application=InterestRateApplication.WholeMonth,
    )


@dataclass(frozen=True, slots=True)
class LoanSnapshot:
    """A plan's position on a date: what is owed, at what rate, for how many more payments."""

    balance: Decimal
    rate: Decimal
    remaining_months: int
    currency: str


def loan_snapshot(plan: Plan, as_of: datetime.date) -> LoanSnapshot:
    cutoff = (as_of.year, as_of.month)
    balance = plan.amount
    remaining = 0
    for installment in plan.generate().installments:
        if (installment.year, int(installment.month)) < cutoff:
            balance = installment.balance.after
        elif installment.i is not None:
            remaining += 1
    if remaining == 0 or balance <= 0:
        raise ValidationError([{"field": "as_of", "message": "The plan is fully paid off by that date"}])
    rate = plan.interest_rate
    for change in sorted(plan.interest_rate_changes, key=lambda item: item.effective_date):
        if change.effective_date <= as_of:
            rate = change.yearly_interest_rate
    return LoanSnapshot(balance=balance, rate=rate, remaining_months=remaining, currency=plan.currency)


@dataclass(frozen=True, slots=True)
class RefinancePlanQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    as_of: datetime.date
    new_rate: Decimal
    new_term_months: int
    closing_costs: Decimal
    roll_costs_into_loan: bool


@dataclass(frozen=True, slots=True)
class PlanRefinance:
    snapshot: LoanSnapshot
    result: RefinanceResult


class RefinancePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, query: RefinancePlanQuery) -> PlanRefinance:
        plan = await get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
        snapshot = loan_snapshot(plan, query.as_of)
        result = refinance(
            RefinanceInput(
                current_balance=snapshot.balance,
                current_rate=snapshot.rate,
                remaining_months=snapshot.remaining_months,
                new_rate=query.new_rate,
                new_term_months=query.new_term_months,
                closing_costs=query.closing_costs,
                roll_costs_into_loan=query.roll_costs_into_loan,
            )
        )
        return PlanRefinance(snapshot=snapshot, result=result)


@dataclass(frozen=True, slots=True)
class PrepayVsInvestPlanQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    extra_monthly: Decimal
    annual_return: Decimal


@dataclass(frozen=True, slots=True)
class PlanPrepayVsInvest:
    principal: Decimal
    interest_rate: Decimal
    term_months: int
    currency: str
    result: PrepayVsInvestResult


class PrepayVsInvestPlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, query: PrepayVsInvestPlanQuery) -> PlanPrepayVsInvest:
        plan = await get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
        data = PrepayVsInvestInput(
            principal=plan.amount,
            interest_rate=plan.interest_rate,
            term_months=plan.term.periods,
            extra_monthly=query.extra_monthly,
            annual_return=query.annual_return,
        )
        return PlanPrepayVsInvest(
            principal=data.principal,
            interest_rate=data.interest_rate,
            term_months=data.term_months,
            currency=plan.currency,
            result=prepay_vs_invest(data),
        )
