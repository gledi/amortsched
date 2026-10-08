import datetime
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from amortsched.app.access import get_owned_plan
from amortsched.core.amortization import AmortizationSchedule, monthly_dates, next_month, recurrence_dates
from amortsched.core.calculators import (
    PeriodRow,
    PrepayVsInvestInput,
    PrepayVsInvestResult,
    RefinanceResult,
    period_rows,
    prepay_vs_invest_from_periods,
    refinance_from_periods,
    validate_prepay_vs_invest,
)
from amortsched.core.entities import Plan
from amortsched.core.errors import ValidationError
from amortsched.core.money import ZERO
from amortsched.core.repositories import AsyncRepository
from amortsched.core.utils import today
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


def _compare_refinance(
    *,
    current: Sequence[PeriodRow],
    current_balance: Decimal,
    new_loan: Callable[[Decimal], AmortizationSchedule],
    new_start: datetime.date,
    closing_costs: Decimal,
    roll_costs_into_loan: bool,
) -> RefinanceResult:
    """Compare keeping the current loan's periods with a new loan built for the refinanced principal.

    Rolled-in closing costs join the new principal; otherwise they are due in cash at closing.
    """
    new_principal = current_balance + (closing_costs if roll_costs_into_loan else ZERO)
    return refinance_from_periods(
        current=current,
        current_balance=current_balance,
        new=period_rows(new_loan(new_principal).generate(new_start)),
        new_principal=new_principal,
        cash_due=ZERO if roll_costs_into_loan else closing_costs,
    )


@dataclass(frozen=True, kw_only=True, slots=True)
class RefinanceTermsQuery:
    """A refinance of loan terms entered without a plan; both loans start on `as_of`, today when omitted."""

    as_of: datetime.date | None
    current_balance: Decimal
    current_rate: Decimal
    remaining_months: int
    new_rate: Decimal
    new_term_months: int
    closing_costs: Decimal
    roll_costs_into_loan: bool


def _as_of_or_today(as_of: datetime.date | None) -> datetime.date:
    return as_of or today()


def refinance_on_terms(query: RefinanceTermsQuery) -> RefinanceResult:
    as_of = _as_of_or_today(query.as_of)
    current = entered_terms_schedule(query.current_balance, query.current_rate, query.remaining_months)
    return _compare_refinance(
        current=period_rows(current.generate(as_of)),
        current_balance=query.current_balance,
        new_loan=lambda principal: entered_terms_schedule(principal, query.new_rate, query.new_term_months),
        new_start=as_of,
        closing_costs=query.closing_costs,
        roll_costs_into_loan=query.roll_costs_into_loan,
    )


@dataclass(frozen=True, slots=True)
class LoanSnapshot:
    """A plan's position on a date: what is owed, at what rate, for how many more payments."""

    balance: Decimal
    rate: Decimal
    remaining_months: int
    currency: str


@dataclass(frozen=True, slots=True)
class _RemainingPlan:
    snapshot: LoanSnapshot
    periods: list[PeriodRow]
    first_period_start: datetime.date


def _first_kept_period(plan: Plan, as_of: datetime.date) -> tuple[int, datetime.date]:
    """How many of the plan's periods start before the `as_of` month, and when the first kept one starts."""
    cutoff = (as_of.year, as_of.month)
    return next(
        (skipped, start)
        for skipped, start in enumerate(monthly_dates(plan.start_date))
        if (start.year, start.month) >= cutoff
    )


def _remaining_plan(plan: Plan, as_of: datetime.date) -> _RemainingPlan:
    """The plan's payment periods from the `as_of` month on, with extras kept in the period they fall in."""
    schedule = plan.to_schedule()
    rows = period_rows(schedule.generate(plan.start_date))
    skipped, first_period_start = _first_kept_period(plan, as_of)
    kept = rows[skipped:]
    remaining_months = sum(1 for row in kept if row.scheduled_payment > 0)
    if remaining_months == 0:
        raise ValidationError([{"field": "as_of", "message": "The plan is fully paid off by that date"}])
    snapshot = LoanSnapshot(
        balance=rows[skipped - 1].balance if skipped else plan.amount,
        rate=schedule.yearly_rate_percent_on(first_period_start),
        remaining_months=remaining_months,
        currency=plan.currency,
    )
    return _RemainingPlan(snapshot=snapshot, periods=kept, first_period_start=first_period_start)


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
            for date in recurrence_dates(recurring):
                if date >= start:
                    schedule.add_recurring_extra_payment(date, recurring.amount, count=1)
        return schedule

    return build


@dataclass(frozen=True, slots=True)
class RefinancePlanQuery:
    """A refinance of a saved plan from the `as_of` month on, today's month when `as_of` is omitted."""

    plan_id: uuid.UUID
    user_id: uuid.UUID
    as_of: datetime.date | None
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
        current = _remaining_plan(plan, _as_of_or_today(query.as_of))
        result = _compare_refinance(
            current=current.periods,
            current_balance=current.snapshot.balance,
            new_loan=_refinanced_plan_loan(plan, current.first_period_start, query.new_rate, query.new_term_months),
            new_start=current.first_period_start,
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
            result=_prepay_vs_invest_on_schedules(plan.to_schedule, data, plan.start_date),
        )


def prepay_vs_invest_on_terms(
    data: PrepayVsInvestInput, start_date: datetime.date | None = None
) -> PrepayVsInvestResult:
    """Prepay vs invest for entered terms, on engine schedules whose first period starts on `start_date`.

    `start_date` defaults to the 1st of next month.
    """
    return _prepay_vs_invest_on_schedules(
        lambda: entered_terms_schedule(data.principal, data.interest_rate, data.term_months),
        data,
        start_date or next_month(today().replace(day=1)),
    )


def _prepay_vs_invest_on_schedules(
    build_baseline: Callable[[], AmortizationSchedule], data: PrepayVsInvestInput, start_date: datetime.date
) -> PrepayVsInvestResult:
    validate_prepay_vs_invest(data)
    baseline = build_baseline()
    prepay = build_baseline()
    prepay.add_recurring_extra_payment(start_date, data.extra_monthly, count=data.term_months)
    return prepay_vs_invest_from_periods(
        baseline=period_rows(baseline.generate(start_date)),
        prepay=period_rows(prepay.generate(start_date)),
        regular_payment=baseline.starting_payment(start_date),
        extra_monthly=data.extra_monthly,
        annual_return=data.annual_return,
    )
