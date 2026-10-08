"""Decision Tools that answer what-if questions about a loan.

Refinance and prepay-vs-invest compare `PeriodRow`s grouped from schedule-engine installments, so
they see the same payments, rate changes, extras and fees as the plan itself. Affordability works
from the level-payment formula alone.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from amortsched.core.errors import ValidationError
from amortsched.core.money import CENT, HUNDRED, ZERO, floor_units, round_cents, round_percent
from amortsched.core.payments import TWELVE, monthly_payment, payment_factor
from amortsched.core.values import Installment

MAX_MONTHS = 600


@dataclass(frozen=True, kw_only=True, slots=True)
class PeriodRow:
    """One payment period of a schedule: everything paid in it and what is owed after it.

    `scheduled_payment` is the period's scheduled installment alone; it is zero for an extra-only period.
    """

    outflow: Decimal
    scheduled_payment: Decimal
    interest: Decimal
    fees: Decimal
    principal: Decimal
    balance: Decimal


def period_rows(installments: Iterable[Installment]) -> list[PeriodRow]:
    """Group schedule-engine installments into one row per payment period.

    The engine yields a period's extra payments before its scheduled payment, so a period closes at
    each scheduled row; extra payments left over at the end form a final period of their own.
    """
    rows: list[PeriodRow] = []
    pending: list[Installment] = []
    for installment in installments:
        pending.append(installment)
        if installment.i is not None:
            rows.append(_merge_period(pending))
            pending = []
    if pending:
        rows.append(_merge_period(pending))
    return rows


def _merge_period(installments: list[Installment]) -> PeriodRow:
    payments = [installment.payment for installment in installments]
    return PeriodRow(
        outflow=sum((payment.total for payment in payments), ZERO),
        scheduled_payment=sum((item.payment.total for item in installments if item.i is not None), ZERO),
        interest=sum((payment.interest for payment in payments), ZERO),
        fees=sum((payment.fees for payment in payments), ZERO),
        principal=sum((payment.principal for payment in payments), ZERO),
        balance=installments[-1].balance.after,
    )


def _require(errors: list[dict[str, str]], condition: bool, field: str, message: str) -> None:
    if not condition:
        errors.append({"field": field, "message": message})


def _validate_loan(errors: list[dict[str, str]], prefix: str, rate: Decimal, months: int) -> None:
    _require(errors, ZERO <= rate <= HUNDRED, f"{prefix}rate", "Interest rate must be between 0 and 100")
    _require(errors, 1 <= months <= MAX_MONTHS, f"{prefix}months", f"Term must be 1 to {MAX_MONTHS} months")


# Affordability


class LimitingRatio(StrEnum):
    FrontEnd = "front_end"
    BackEnd = "back_end"


@dataclass(frozen=True, kw_only=True, slots=True)
class AffordabilityInput:
    gross_monthly_income: Decimal
    monthly_debts: Decimal
    down_payment: Decimal
    interest_rate: Decimal
    term_months: int
    property_tax_rate: Decimal = ZERO
    insurance_annual: Decimal = ZERO
    hoa_monthly: Decimal = ZERO
    pmi_annual_rate: Decimal = ZERO
    front_end_ratio: Decimal = Decimal("28")
    back_end_ratio: Decimal = Decimal("36")


@dataclass(frozen=True, kw_only=True, slots=True)
class MonthlyHousingBreakdown:
    principal_interest: Decimal
    property_tax: Decimal
    insurance: Decimal
    hoa: Decimal
    pmi: Decimal

    @property
    def total(self) -> Decimal:
        return self.principal_interest + self.property_tax + self.insurance + self.hoa + self.pmi


@dataclass(frozen=True, kw_only=True, slots=True)
class AffordabilityResult:
    max_home_price: Decimal
    max_loan_amount: Decimal
    max_monthly_housing: Decimal
    limiting_ratio: LimitingRatio
    monthly: MonthlyHousingBreakdown
    front_end_ratio: Decimal
    back_end_ratio: Decimal
    ltv: Decimal | None
    down_payment_percent: Decimal | None


def _housing_cost(price: Decimal, data: AffordabilityInput, pmi_active: bool) -> MonthlyHousingBreakdown:
    loan = max(ZERO, price - data.down_payment)
    return MonthlyHousingBreakdown(
        principal_interest=monthly_payment(loan, data.interest_rate, data.term_months),
        property_tax=round_cents(price * data.property_tax_rate / HUNDRED / TWELVE),
        insurance=round_cents(data.insurance_annual / TWELVE),
        hoa=data.hoa_monthly,
        pmi=round_cents(loan * data.pmi_annual_rate / HUNDRED / TWELVE) if pmi_active else ZERO,
    )


def _max_price(data: AffordabilityInput, budget: Decimal) -> tuple[Decimal, bool]:
    """Highest price whose full monthly housing cost fits the budget, and whether PMI applies there."""
    fixed = data.insurance_annual / TWELVE + data.hoa_monthly
    tax = data.property_tax_rate / HUNDRED / TWELVE
    factor = payment_factor(data.interest_rate, data.term_months)
    pmi = data.pmi_annual_rate / HUNDRED / TWELVE
    available = budget - fixed
    if available <= 0:
        return ZERO, False

    price = (available + data.down_payment * factor) / (tax + factor)
    if price <= data.down_payment:
        cash_limit = available / tax if tax > 0 else data.down_payment
        return min(data.down_payment, cash_limit), False

    needs_pmi = pmi > 0 and (price - data.down_payment) / price > Decimal("0.8")
    if not needs_pmi:
        return price, False

    with_pmi = (available + data.down_payment * (factor + pmi)) / (tax + factor + pmi)
    if (with_pmi - data.down_payment) / with_pmi > Decimal("0.8"):
        return with_pmi, True
    return data.down_payment / Decimal("0.2"), False


def affordability(data: AffordabilityInput) -> AffordabilityResult:
    errors: list[dict[str, str]] = []
    _require(errors, data.gross_monthly_income > 0, "gross_monthly_income", "Income must be positive")
    for field in ("monthly_debts", "down_payment", "property_tax_rate", "insurance_annual", "hoa_monthly"):
        _require(errors, getattr(data, field) >= 0, field, "Must be zero or greater")
    _require(errors, ZERO <= data.pmi_annual_rate <= HUNDRED, "pmi_annual_rate", "PMI rate must be 0-100%")
    _require(errors, ZERO < data.front_end_ratio <= HUNDRED, "front_end_ratio", "Ratio must be 0-100%")
    _require(errors, ZERO < data.back_end_ratio <= HUNDRED, "back_end_ratio", "Ratio must be 0-100%")
    _validate_loan(errors, "interest_", data.interest_rate, data.term_months)
    if errors:
        raise ValidationError(errors)

    front_budget = data.gross_monthly_income * data.front_end_ratio / HUNDRED
    back_budget = data.gross_monthly_income * data.back_end_ratio / HUNDRED - data.monthly_debts
    budget = min(front_budget, back_budget)
    limiting = LimitingRatio.FrontEnd if front_budget <= back_budget else LimitingRatio.BackEnd

    price, pmi_active = _max_price(data, budget)
    price = floor_units(price)
    loan = max(ZERO, price - data.down_payment)
    monthly = _housing_cost(price, data, pmi_active)
    total = monthly.total
    return AffordabilityResult(
        max_home_price=price,
        max_loan_amount=loan,
        max_monthly_housing=max(ZERO, budget),
        limiting_ratio=limiting,
        monthly=monthly,
        front_end_ratio=total / data.gross_monthly_income * HUNDRED,
        back_end_ratio=(total + data.monthly_debts) / data.gross_monthly_income * HUNDRED,
        ltv=loan / price * HUNDRED if price > 0 else None,
        down_payment_percent=min(data.down_payment, price) / price * HUNDRED if price > 0 else None,
    )


# Refinance


@dataclass(frozen=True, kw_only=True, slots=True)
class RefinanceResult:
    current_payment: Decimal
    new_payment: Decimal
    monthly_savings: Decimal
    new_principal: Decimal
    cash_due_at_closing: Decimal
    current_total_interest: Decimal
    new_total_interest: Decimal
    current_total_paid: Decimal
    new_total_paid: Decimal
    lifetime_savings: Decimal
    break_even_month: int | None
    advantage_by_month: tuple[Decimal, ...]


def refinance_from_periods(
    *,
    current: Sequence[PeriodRow],
    current_balance: Decimal,
    new: Sequence[PeriodRow],
    new_principal: Decimal,
    cash_due: Decimal,
) -> RefinanceResult:
    """Compare keeping the current loan with refinancing, period by period."""

    def position(rows: Sequence[PeriodRow], month: int, start: Decimal, upfront: Decimal) -> Decimal:
        """Money paid so far plus what is still owed: lower is better."""
        paid = sum((row.outflow for row in rows[:month]), ZERO)
        owed = rows[month - 1].balance if 0 < month <= len(rows) else (start if month == 0 else ZERO)
        return upfront + paid + owed

    horizon = max(len(current), len(new))
    advantage: list[Decimal] = []
    break_even: int | None = None
    for month in range(0, horizon + 1):
        gap = position(current, month, current_balance, ZERO) - position(new, month, new_principal, cash_due)
        advantage.append(round_cents(gap))
        if break_even is None and month > 0 and gap >= 0:
            break_even = month

    current_paid = sum((row.outflow for row in current), ZERO)
    new_paid = sum((row.outflow for row in new), ZERO) + cash_due
    current_payment = _first_scheduled_payment(current)
    new_payment = _first_scheduled_payment(new)
    return RefinanceResult(
        current_payment=current_payment,
        new_payment=new_payment,
        monthly_savings=current_payment - new_payment,
        new_principal=new_principal,
        cash_due_at_closing=cash_due,
        current_total_interest=sum((row.interest for row in current), ZERO),
        new_total_interest=sum((row.interest for row in new), ZERO),
        current_total_paid=current_paid,
        new_total_paid=new_paid,
        lifetime_savings=current_paid - new_paid,
        break_even_month=break_even,
        advantage_by_month=tuple(advantage),
    )


def _first_scheduled_payment(rows: Sequence[PeriodRow]) -> Decimal:
    return next((row.scheduled_payment for row in rows if row.scheduled_payment > 0), ZERO)


# Prepay vs invest


@dataclass(frozen=True, kw_only=True, slots=True)
class PrepayVsInvestInput:
    principal: Decimal
    interest_rate: Decimal
    term_months: int
    extra_monthly: Decimal
    annual_return: Decimal


class Strategy(StrEnum):
    Prepay = "prepay"
    Invest = "invest"
    Tie = "tie"


@dataclass(frozen=True, kw_only=True, slots=True)
class NetWorthPoint:
    month: int
    prepay: Decimal
    invest: Decimal


@dataclass(frozen=True, kw_only=True, slots=True)
class PrepayVsInvestResult:
    regular_payment: Decimal
    payoff_months_with_prepayment: int
    months_saved: int
    interest_without_prepayment: Decimal
    interest_with_prepayment: Decimal
    interest_saved: Decimal
    prepay_net_worth: Decimal
    invest_net_worth: Decimal
    advantage: Decimal
    better_strategy: Strategy
    break_even_return: Decimal | None
    timeline: tuple[NetWorthPoint, ...]


@dataclass(frozen=True, kw_only=True, slots=True)
class _PrepayRuns:
    baseline: Sequence[PeriodRow]
    prepay: Sequence[PeriodRow]
    extra_monthly: Decimal


def _net_worths(runs: _PrepayRuns, annual_return: Decimal) -> list[NetWorthPoint]:
    growth = 1 + annual_return / HUNDRED / TWELVE
    prepay_savings = ZERO
    invest_savings = ZERO
    points: list[NetWorthPoint] = []
    for month, baseline_row in enumerate(runs.baseline, start=1):
        available = baseline_row.outflow + runs.extra_monthly
        if month <= len(runs.prepay):
            row = runs.prepay[month - 1]
            leftover = available - row.outflow
            prepay_debt = row.balance
        else:
            leftover = available
            prepay_debt = ZERO
        prepay_savings = prepay_savings * growth + leftover
        invest_savings = invest_savings * growth + runs.extra_monthly
        points.append(
            NetWorthPoint(
                month=month,
                prepay=prepay_savings - prepay_debt,
                invest=invest_savings - baseline_row.balance,
            )
        )
    return points


def _break_even_return(runs: _PrepayRuns) -> Decimal | None:
    def gap(annual_return: Decimal) -> Decimal:
        final = _net_worths(runs, annual_return)[-1]
        return final.invest - final.prepay

    low, high = ZERO, Decimal("50")
    low_gap, high_gap = gap(low), gap(high)
    if low_gap >= 0 or high_gap <= 0:
        return None
    for _ in range(40):
        middle = (low + high) / 2
        if gap(middle) > 0:
            high = middle
        else:
            low = middle
        if high - low < Decimal("0.0001"):
            break
    return round_percent((low + high) / 2)


def validate_prepay_vs_invest(data: PrepayVsInvestInput) -> None:
    errors: list[dict[str, str]] = []
    _require(errors, data.principal > 0, "principal", "Principal must be positive")
    _require(errors, data.extra_monthly > 0, "extra_monthly", "Extra payment must be positive")
    in_range = Decimal("-50") <= data.annual_return <= Decimal("50")
    _require(errors, in_range, "annual_return", "Return must be between -50% and 50%")
    _validate_loan(errors, "interest_", data.interest_rate, data.term_months)
    if errors:
        raise ValidationError(errors)


def prepay_vs_invest_from_periods(
    *,
    baseline: Sequence[PeriodRow],
    prepay: Sequence[PeriodRow],
    regular_payment: Decimal,
    extra_monthly: Decimal,
    annual_return: Decimal,
) -> PrepayVsInvestResult:
    """Compare prepaying the loan with investing the extra, period by period over the baseline loan."""
    runs = _PrepayRuns(baseline=baseline, prepay=prepay, extra_monthly=extra_monthly)
    timeline = _net_worths(runs, annual_return)
    final = timeline[-1]
    advantage = final.prepay - final.invest
    if abs(advantage) < CENT:
        better = Strategy.Tie
    else:
        better = Strategy.Prepay if advantage > 0 else Strategy.Invest
    interest_plain = sum((row.interest for row in baseline), ZERO)
    interest_prepay = sum((row.interest for row in prepay), ZERO)
    return PrepayVsInvestResult(
        regular_payment=regular_payment,
        payoff_months_with_prepayment=len(prepay),
        months_saved=len(baseline) - len(prepay),
        interest_without_prepayment=interest_plain,
        interest_with_prepayment=interest_prepay,
        interest_saved=interest_plain - interest_prepay,
        prepay_net_worth=final.prepay,
        invest_net_worth=final.invest,
        advantage=abs(advantage),
        better_strategy=better,
        break_even_return=_break_even_return(runs),
        timeline=tuple(timeline),
    )
