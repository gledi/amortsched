"""Decision calculators over plain monthly amortization.

These model a loan's base terms (fixed rate, level payment, payments at month end) to answer
what-if questions. Plan schedules with dated adjustments come from `amortization.py` instead.
"""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum

from amortsched.core.errors import ValidationError
from amortsched.core.money import CENT, HUNDRED, ZERO, round_cents, round_percent
from amortsched.core.payments import TWELVE, monthly_payment, monthly_rate, payment_factor

MAX_MONTHS = 600


@dataclass(frozen=True, slots=True)
class AmortizationMonth:
    month: int
    payment: Decimal
    interest: Decimal
    principal: Decimal
    extra: Decimal
    balance: Decimal


def amortize(
    principal: Decimal,
    annual_rate_percent: Decimal,
    months: int,
    extra_monthly: Decimal = ZERO,
) -> list[AmortizationMonth]:
    """Level-payment schedule; any extra goes to principal after each scheduled payment."""
    rate = monthly_rate(annual_rate_percent)
    payment = monthly_payment(principal, annual_rate_percent, months)
    balance = principal
    rows: list[AmortizationMonth] = []
    for month in range(1, months + 1):
        if balance <= 0:
            break
        interest = round_cents(balance * rate)
        scheduled_principal = min(payment - interest, balance) if month < months else balance
        balance -= scheduled_principal
        extra = min(extra_monthly, balance)
        balance -= extra
        rows.append(
            AmortizationMonth(
                month=month,
                payment=scheduled_principal + interest,
                interest=interest,
                principal=scheduled_principal,
                extra=extra,
                balance=balance,
            )
        )
    return rows


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
    price = price.quantize(Decimal("1"), rounding=ROUND_FLOOR)
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
class RefinanceInput:
    current_balance: Decimal
    current_rate: Decimal
    remaining_months: int
    new_rate: Decimal
    new_term_months: int
    closing_costs: Decimal = ZERO
    roll_costs_into_loan: bool = False


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


def refinance(data: RefinanceInput) -> RefinanceResult:
    errors: list[dict[str, str]] = []
    _require(errors, data.current_balance > 0, "current_balance", "Balance must be positive")
    _require(errors, data.closing_costs >= 0, "closing_costs", "Closing costs must be zero or greater")
    _validate_loan(errors, "current_", data.current_rate, data.remaining_months)
    _validate_loan(errors, "new_", data.new_rate, data.new_term_months)
    if errors:
        raise ValidationError(errors)

    new_principal = data.current_balance + (data.closing_costs if data.roll_costs_into_loan else ZERO)
    cash_due = ZERO if data.roll_costs_into_loan else data.closing_costs
    current = amortize(data.current_balance, data.current_rate, data.remaining_months)
    new = amortize(new_principal, data.new_rate, data.new_term_months)

    def position(rows: list[AmortizationMonth], month: int, start: Decimal, upfront: Decimal) -> Decimal:
        """Money paid so far plus what is still owed: lower is better."""
        paid = sum((row.payment for row in rows[:month]), ZERO)
        owed = rows[month - 1].balance if 0 < month <= len(rows) else (start if month == 0 else ZERO)
        return upfront + paid + owed

    horizon = max(len(current), len(new))
    advantage: list[Decimal] = []
    break_even: int | None = None
    for month in range(0, horizon + 1):
        gap = position(current, month, data.current_balance, ZERO) - position(new, month, new_principal, cash_due)
        advantage.append(round_cents(gap))
        if break_even is None and month > 0 and gap >= 0:
            break_even = month

    current_paid = sum((row.payment for row in current), ZERO)
    new_paid = sum((row.payment for row in new), ZERO) + cash_due
    current_payment = current[0].payment
    new_payment = new[0].payment
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


def _net_worths(data: PrepayVsInvestInput, annual_return: Decimal) -> list[NetWorthPoint]:
    growth = 1 + annual_return / HUNDRED / TWELVE
    payment = monthly_payment(data.principal, data.interest_rate, data.term_months)
    prepay = amortize(data.principal, data.interest_rate, data.term_months, data.extra_monthly)
    plain = amortize(data.principal, data.interest_rate, data.term_months)
    prepay_savings = ZERO
    invest_savings = ZERO
    points: list[NetWorthPoint] = []
    for month in range(1, data.term_months + 1):
        if month <= len(prepay):
            row = prepay[month - 1]
            leftover = (payment - row.payment) + (data.extra_monthly - row.extra)
            prepay_debt = row.balance
        else:
            leftover = payment + data.extra_monthly
            prepay_debt = ZERO
        prepay_savings = prepay_savings * growth + leftover
        invest_savings = invest_savings * growth + data.extra_monthly
        invest_debt = plain[month - 1].balance if month <= len(plain) else ZERO
        points.append(
            NetWorthPoint(month=month, prepay=prepay_savings - prepay_debt, invest=invest_savings - invest_debt)
        )
    return points


def _break_even_return(data: PrepayVsInvestInput) -> Decimal | None:
    def gap(annual_return: Decimal) -> Decimal:
        final = _net_worths(data, annual_return)[-1]
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


def prepay_vs_invest(data: PrepayVsInvestInput) -> PrepayVsInvestResult:
    errors: list[dict[str, str]] = []
    _require(errors, data.principal > 0, "principal", "Principal must be positive")
    _require(errors, data.extra_monthly > 0, "extra_monthly", "Extra payment must be positive")
    in_range = Decimal("-50") <= data.annual_return <= Decimal("50")
    _require(errors, in_range, "annual_return", "Return must be between -50% and 50%")
    _validate_loan(errors, "interest_", data.interest_rate, data.term_months)
    if errors:
        raise ValidationError(errors)

    plain = amortize(data.principal, data.interest_rate, data.term_months)
    prepay = amortize(data.principal, data.interest_rate, data.term_months, data.extra_monthly)
    timeline = _net_worths(data, data.annual_return)
    final = timeline[-1]
    advantage = final.prepay - final.invest
    if abs(advantage) < CENT:
        better = Strategy.Tie
    else:
        better = Strategy.Prepay if advantage > 0 else Strategy.Invest
    interest_plain = sum((row.interest for row in plain), ZERO)
    interest_prepay = sum((row.interest for row in prepay), ZERO)
    return PrepayVsInvestResult(
        regular_payment=monthly_payment(data.principal, data.interest_rate, data.term_months),
        payoff_months_with_prepayment=len(prepay),
        months_saved=len(plain) - len(prepay),
        interest_without_prepayment=interest_plain,
        interest_with_prepayment=interest_prepay,
        interest_saved=interest_plain - interest_prepay,
        prepay_net_worth=final.prepay,
        invest_net_worth=final.invest,
        advantage=abs(advantage),
        better_strategy=better,
        break_even_return=_break_even_return(data),
        timeline=tuple(timeline),
    )
