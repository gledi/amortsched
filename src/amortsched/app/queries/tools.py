import datetime
import uuid
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from decimal import Decimal

from amortsched.app.access import get_owned_plan
from amortsched.core.amortization import AmortizationSchedule, next_month
from amortsched.core.calculators import (
    PrepayVsInvestInput,
    PrepayVsInvestResult,
    RefinanceResult,
    period_rows,
    prepay_vs_invest,
    prepay_vs_invest_from_periods,
    refinance_from_periods,
    validate_prepay_vs_invest,
)
from amortsched.core.entities import Plan
from amortsched.core.errors import ValidationError
from amortsched.core.money import ZERO
from amortsched.core.repositories import AsyncRepository
from amortsched.core.values import Installment, InterestRateApplication, RecurringExtraPayment


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


def compare_refinance(
    *,
    current: Iterable[Installment],
    current_balance: Decimal,
    new_loan: Callable[[Decimal], AmortizationSchedule],
    new_start: datetime.date,
    closing_costs: Decimal,
    roll_costs_into_loan: bool,
) -> RefinanceResult:
    """Compare keeping the current loan's installments with a new loan built for the refinanced principal.

    Rolled-in closing costs join the new principal; otherwise they are due in cash at closing.
    """
    new_principal = current_balance + (closing_costs if roll_costs_into_loan else ZERO)
    return refinance_from_periods(
        current=period_rows(current),
        current_balance=current_balance,
        new=period_rows(new_loan(new_principal).generate(new_start)),
        new_principal=new_principal,
        cash_due=ZERO if roll_costs_into_loan else closing_costs,
    )


@dataclass(frozen=True, slots=True)
class LoanSnapshot:
    """A plan's position on a date: what is owed, at what rate, for how many more payments."""

    balance: Decimal
    rate: Decimal
    remaining_months: int
    currency: str


@dataclass(frozen=True, slots=True)
class _PlanFromMonth:
    snapshot: LoanSnapshot
    installments: list[Installment]
    first_payment_date: datetime.date


def _plan_from_month(plan: Plan, as_of: datetime.date) -> _PlanFromMonth:
    """The plan's payment periods from the `as_of` month on, with extras kept in the period they fall in."""
    cutoff = (as_of.year, as_of.month)
    balance = plan.amount
    remaining: list[Installment] = []
    period: list[Installment] = []
    for installment in plan.generate().installments:
        period.append(installment)
        if installment.i is None:
            continue
        if (installment.year, int(installment.month)) < cutoff:
            balance = installment.balance.after
        else:
            remaining.extend(period)
        period = []
    remaining.extend(period)
    scheduled = sum(1 for installment in remaining if installment.i is not None)
    if scheduled == 0 or balance <= 0:
        raise ValidationError([{"field": "as_of", "message": "The plan is fully paid off by that date"}])
    rate = plan.interest_rate
    for change in sorted(plan.interest_rate_changes, key=lambda item: item.effective_date):
        if change.effective_date <= as_of:
            rate = change.yearly_interest_rate
    first_payment_date = plan.start_date
    while (first_payment_date.year, first_payment_date.month) < cutoff:
        first_payment_date = next_month(first_payment_date, base_day=plan.start_date.day)
    return _PlanFromMonth(
        snapshot=LoanSnapshot(balance=balance, rate=rate, remaining_months=scheduled, currency=plan.currency),
        installments=remaining,
        first_payment_date=first_payment_date,
    )


def _occurrences(recurring: RecurringExtraPayment) -> Iterator[datetime.date]:
    date = recurring.start_date
    for _ in range(recurring.count):
        yield date
        date = next_month(date, base_day=recurring.start_date.day)


def _refinanced_plan_loan(
    plan: Plan, start: datetime.date, rate: Decimal, months: int
) -> Callable[[Decimal], AmortizationSchedule]:
    """The new lender's loan: the plan's extras from `start` on and its interest mode, no fees or Rate Changes."""

    def build(principal: Decimal) -> AmortizationSchedule:
        schedule = AmortizationSchedule(
            principal,
            (0, months),
            rate,
            interest_rate_application=plan.interest_rate_application,
        )
        for extra in plan.one_time_extra_payments:
            if extra.date >= start:
                schedule.add_one_time_extra_payment(extra.date, extra.amount)
        for recurring in plan.recurring_extra_payments:
            # One per occurrence so a day clamped in a short month can't become the new series' base day.
            for date in _occurrences(recurring):
                if date >= start:
                    schedule.add_recurring_extra_payment(date, recurring.amount, count=1)
        return schedule

    return build


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
        current = _plan_from_month(plan, query.as_of)
        result = compare_refinance(
            current=current.installments,
            current_balance=current.snapshot.balance,
            new_loan=_refinanced_plan_loan(plan, current.first_payment_date, query.new_rate, query.new_term_months),
            new_start=current.first_payment_date,
            closing_costs=query.closing_costs,
            roll_costs_into_loan=query.roll_costs_into_loan,
        )
        return PlanRefinance(snapshot=current.snapshot, result=result)


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


def prepay_vs_invest_on_terms(data: PrepayVsInvestInput, start_date: datetime.date) -> PrepayVsInvestResult:
    """Prepay vs invest for entered terms, on engine schedules whose first period starts on `start_date`."""
    validate_prepay_vs_invest(data)
    baseline = entered_terms_schedule(data.principal, data.interest_rate, data.term_months)
    prepay = entered_terms_schedule(data.principal, data.interest_rate, data.term_months)
    prepay.add_recurring_extra_payment(start_date, data.extra_monthly, count=data.term_months)
    return prepay_vs_invest_from_periods(
        baseline=period_rows(baseline.generate(start_date)),
        prepay=period_rows(prepay.generate(start_date)),
        regular_payment=baseline.starting_payment(start_date),
        extra_monthly=data.extra_monthly,
        annual_return=data.annual_return,
    )
