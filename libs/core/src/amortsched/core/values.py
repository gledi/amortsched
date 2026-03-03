import datetime
import enum
from dataclasses import dataclass
from decimal import Decimal

from amortsched.core.errors import InvalidTermError

type Amount = int | float | Decimal
type TermType = int | tuple[int, int] | Term
type InterestRate = float | Decimal


_DAYS_IN_YEAR = Decimal("365")


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


@dataclass(kw_only=True, slots=True)
class EarlyPaymentFees:
    fixed: Amount = Decimal("0.00")
    percent: Amount = Decimal("0.00")

    def penalty(self, amount: Amount) -> Decimal:
        fixed = self.fixed if isinstance(self.fixed, Decimal) else Decimal(self.fixed)
        percent = self.percent if isinstance(self.percent, Decimal) else Decimal(self.percent)

        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        percent_fee = amount * (percent / Decimal("100.00"))
        return fixed + percent_fee

    def principal(self, amount: Amount) -> Decimal:
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        penalty = self.penalty(amount)
        return amount - penalty


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

    @property
    def total_outflow(self) -> Decimal:
        return self.principal + self.interest + self.fees


@dataclass
class Term:
    years: int
    months: int = 0

    def __post_init__(self):
        if self.years < 0 or self.months < 0:
            raise InvalidTermError("Years and months must be non-negative", self)
        total_months = self.years * 12 + self.months
        self.years = total_months // 12
        self.months = total_months % 12

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
