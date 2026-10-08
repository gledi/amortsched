import datetime
import enum
import re
from dataclasses import dataclass
from decimal import Decimal

from amortsched.core.errors import InvalidTermError, ValidationError
from amortsched.core.money import HUNDRED, ZERO, round_cents

type Amount = int | float | Decimal
type TermType = int | tuple[int, int] | Term
type InterestRate = float | Decimal


DAYS_IN_YEAR = Decimal("365")
DEFAULT_CURRENCY = "USD"

_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


def normalize_currency(code: str, field: str = "currency") -> str:
    normalized = code.strip().upper()
    if not _CURRENCY_CODE.fullmatch(normalized):
        raise ValidationError([{"field": field, "message": "Currency must be a three-letter ISO 4217 code"}])
    return normalized


class Month(enum.IntEnum):
    January = 1
    February = 2
    March = 3
    April = 4
    May = 5
    June = 6
    July = 7
    August = 8
    September = 9
    October = 10
    November = 11
    December = 12


@dataclass(frozen=True, kw_only=True, slots=True)
class EarlyPaymentFees:
    fixed: Amount = ZERO
    percent: Amount = ZERO

    def __post_init__(self) -> None:
        fixed = self.fixed if isinstance(self.fixed, Decimal) else Decimal(self.fixed)
        percent = self.percent if isinstance(self.percent, Decimal) else Decimal(self.percent)
        if fixed < ZERO:
            raise ValueError("Early payment fixed fee cannot be negative")
        if percent < ZERO or percent > HUNDRED:
            raise ValueError("Early payment percent fee must be between 0 and 100")

    def penalty(self, amount: Amount) -> Decimal:
        fixed = self.fixed if isinstance(self.fixed, Decimal) else Decimal(self.fixed)
        percent = self.percent if isinstance(self.percent, Decimal) else Decimal(self.percent)

        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        percent_fee = amount * (percent / HUNDRED)
        return round_cents(fixed + percent_fee)

    def principal(self, amount: Amount) -> Decimal:
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        penalty = self.penalty(amount)
        return max(ZERO, amount - penalty)


class LoanType(enum.StrEnum):
    Mortgage = "mortgage"
    Auto = "auto"
    Personal = "personal"
    Student = "student"
    Other = "other"


@dataclass(frozen=True, slots=True)
class HousingPayment:
    property_tax: Decimal
    insurance: Decimal
    hoa: Decimal
    pmi: Decimal

    @property
    def escrow(self) -> Decimal:
        return self.property_tax + self.insurance + self.hoa

    @property
    def total(self) -> Decimal:
        return self.escrow + self.pmi


@dataclass(frozen=True, kw_only=True, slots=True)
class HousingCosts:
    """Ownership costs paid alongside a mortgage. Only PMI is a cost of the loan itself."""

    property_value: Decimal | None = None
    property_tax_annual: Decimal = ZERO
    insurance_annual: Decimal = ZERO
    hoa_monthly: Decimal = ZERO
    pmi_annual_rate: Decimal = ZERO
    pmi_cancel_ltv: Decimal = Decimal("78")

    def __post_init__(self) -> None:
        errors: list[dict[str, str]] = []
        if self.property_value is not None and self.property_value <= 0:
            errors.append({"field": "housing_costs.property_value", "message": "Property value must be positive"})
        for name in ("property_tax_annual", "insurance_annual", "hoa_monthly", "pmi_annual_rate"):
            if getattr(self, name) < 0:
                errors.append({"field": f"housing_costs.{name}", "message": "Must be zero or greater"})
        if self.pmi_annual_rate > 100:
            errors.append({"field": "housing_costs.pmi_annual_rate", "message": "PMI rate must be at most 100%"})
        if not ZERO < self.pmi_cancel_ltv <= HUNDRED:
            errors.append({"field": "housing_costs.pmi_cancel_ltv", "message": "PMI cancellation LTV must be 0-100%"})
        if self.pmi_annual_rate > 0 and self.property_value is None:
            errors.append({"field": "housing_costs.property_value", "message": "PMI requires a property value"})
        if errors:
            raise ValidationError(errors)

    @property
    def is_empty(self) -> bool:
        return (
            self.property_value is None
            and self.property_tax_annual == 0
            and self.insurance_annual == 0
            and self.hoa_monthly == 0
            and self.pmi_annual_rate == 0
        )

    @property
    def has_pmi(self) -> bool:
        return self.pmi_annual_rate > 0 and self.property_value is not None

    def ltv_percent(self, balance: Decimal) -> Decimal | None:
        if self.property_value is None:
            return None
        return balance / self.property_value * HUNDRED

    def pmi_applies(self, balance: Decimal) -> bool:
        ltv = self.ltv_percent(balance)
        return self.has_pmi and ltv is not None and ltv > self.pmi_cancel_ltv

    def down_payment(self, loan_amount: Decimal) -> Decimal | None:
        if self.property_value is None:
            return None
        return max(ZERO, self.property_value - loan_amount)

    def monthly_payment(self, *, loan_amount: Decimal, pmi_active: bool) -> HousingPayment:
        pmi = loan_amount * self.pmi_annual_rate / HUNDRED / Decimal("12") if pmi_active else ZERO
        return HousingPayment(
            property_tax=self.property_tax_annual / Decimal("12"),
            insurance=self.insurance_annual / Decimal("12"),
            hoa=self.hoa_monthly,
            pmi=pmi,
        )


class PaymentKind(enum.StrEnum):
    ScheduledPayment = "scheduled"
    OneTimeExtraPayment = "one_time_extra"
    RecurringExtraPayment = "recurring_extra"


@dataclass
class Payment:
    kind: PaymentKind
    principal: Decimal
    interest: Decimal
    fees: Decimal

    @property
    def total(self) -> Decimal:
        return self.principal + self.interest + self.fees


@dataclass
class OneTimeExtraPayment:
    date: datetime.date
    amount: Decimal


@dataclass
class RecurringExtraPayment:
    start_date: datetime.date
    amount: Decimal
    count: int


@dataclass
class ScheduleTotals:
    principal: Decimal
    interest: Decimal
    fees: Decimal
    months: int
    paid_off: bool
    pmi: Decimal = ZERO
    escrow: Decimal = ZERO

    @property
    def total_outflow(self) -> Decimal:
        return self.principal + self.interest + self.fees


@dataclass(frozen=True)
class Term:
    years: int
    months: int = 0

    def __post_init__(self):
        if self.years < 0 or self.months < 0:
            raise InvalidTermError("Years and months must be non-negative", self)
        total_months = self.years * 12 + self.months
        if total_months == 0:
            raise InvalidTermError("Term must be at least one month", self)
        object.__setattr__(self, "years", total_months // 12)
        object.__setattr__(self, "months", total_months % 12)

    @property
    def periods(self) -> int:
        return self.years * 12 + self.months


@dataclass
class Balance:
    before: Decimal
    after: Decimal


@dataclass
class Installment:
    i: int | None
    year: int
    month: Month
    payment: Payment
    balance: Balance
    housing: HousingPayment | None = None

    @property
    def month_name(self) -> str:
        return self.month.name

    def to_row(self) -> list[str]:
        installment = "" if self.i is None else str(self.i)
        return [
            installment,
            f"{self.year}/{self.month.name}",
            self.payment.kind,
            f"{self.payment.principal:,.2f}",
            f"{self.payment.interest:,.2f}",
            f"{self.payment.fees:,.2f}",
            f"{self.payment.total:,.2f}",
            f"{self.balance.before:,.2f}",
            f"{self.balance.after:,.2f}",
        ]


@dataclass(frozen=True, slots=True)
class InterestRateChange:
    # Annual nominal interest rate in percent (e.g. 5.25 for 5.25%), effective from this date forward.
    effective_date: datetime.date
    yearly_interest_rate: Decimal


class InterestRateApplication(enum.StrEnum):
    # (A) Apply the single rate effective as of the scheduled date to the whole installment month.
    WholeMonth = "whole_month"
    # (B1) If rate changes within the calendar month, prorate interest by day ranges within that month.
    ProratedByDaysInMonth = "prorated_by_days_in_month"
    # (B2) If rate changes within the payment-to-payment period, prorate interest by day ranges within that period.
    ProratedByPaymentPeriod = "prorated_by_payment_period"
