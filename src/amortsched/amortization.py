import calendar
import datetime
import enum
import operator as op
from collections.abc import Generator
from dataclasses import dataclass
from decimal import Decimal

type Amount = int | float | Decimal
type TermType = int | tuple[int, int] | Term
type InterestRate = float | Decimal


class InvalidTermError(Exception):
    def __init__(self, message, term: Term) -> None:
        super().__init__(message)
        self.term = term


class InvalidExtraPaymentError(Exception):
    def __init__(self, message: str, date: datetime.date, amount: Amount) -> None:
        super().__init__(message)
        self.date = date
        self.amount = amount


class InvalidRecurringPaymentError(Exception):
    def __init__(self, message: str, start_date: datetime.date, amount: Amount, count: int) -> None:
        super().__init__(message)
        self.start_date = start_date
        self.amount = amount
        self.count = count


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


@dataclass
class EarlyPaymentFees:
    fixed: Decimal = Decimal("0.00")
    percent: Decimal = Decimal("0.00")

    def penalty(self, amount: Amount) -> Decimal:
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        percent_fee = amount * (self.percent / Decimal("100.00"))
        return self.fixed + percent_fee

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


def next_month(dt: datetime.date) -> datetime.date:
    year, month = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


class AmortizationSchedule:
    def __init__(
        self,
        amount: Amount,
        term: TermType,
        interest_rate: InterestRate,
        early_payment_fees: EarlyPaymentFees | None = None,
    ) -> None:
        self.amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        self.interest_rate = interest_rate if isinstance(interest_rate, Decimal) else Decimal(interest_rate)
        if isinstance(term, int):
            term = (term, 0)
        self.term = Term(*term) if isinstance(term, tuple) else term
        self.early_payment_fees = early_payment_fees if early_payment_fees is not None else EarlyPaymentFees()
        self.one_time_extra_payments: list[OneTimeExtraPayment] = []
        self.recurring_extra_payments: list[RecurringExtraPayment] = []
        self._last_totals: ScheduleTotals | None = None

    def __str__(self) -> str:
        term_parts = [f"{self.term.years} years"]
        if self.term.months > 0:
            term_parts.append(f"{self.term.months} months")
        term = " and ".join(term_parts)
        return f"{self.amount:,.2f} over {term} at {self.interest_rate:.2f}% yearly interest rate"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(amount={self.amount:_.2f}, term={self.term!r}, "
            f"interest_rate={self.interest_rate!r})"
        )

    @property
    def yearly_interest_rate(self) -> Decimal:
        return self.interest_rate / Decimal("100.00")

    @property
    def monthly_interest_rate(self) -> Decimal:
        return self.yearly_interest_rate / Decimal("12.00")

    @property
    def periods(self) -> int:
        return self.term.periods

    @property
    def discount_factor(self) -> Decimal:
        rate = self.monthly_interest_rate
        if rate == 0:
            return Decimal(self.periods)
        return ((1 + rate) ** self.periods - 1) / (rate * (1 + rate) ** self.periods)

    @property
    def monthly_installment(self) -> Decimal:
        return self.amount / self.discount_factor

    @property
    def total_amount_paid(self) -> Decimal:
        if self._last_totals:
            return self._last_totals.total_outflow
        return self.monthly_installment * self.periods

    @property
    def total_interest_paid(self) -> Decimal:
        if self._last_totals:
            return self._last_totals.interest
        return self.total_amount_paid - self.amount

    @property
    def last_totals(self) -> ScheduleTotals | None:
        return self._last_totals

    def add_one_time_extra_payment(self, date: datetime.date, amount: Amount) -> None:
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        if amount <= 0:
            raise InvalidExtraPaymentError("Extra payment amount must be positive", date, amount)
        self.one_time_extra_payments.append(OneTimeExtraPayment(date=date, amount=amount))

    def add_recurring_extra_payment(self, start_date: datetime.date, amount: Amount, *, count: int) -> None:
        if count <= 0:
            raise InvalidRecurringPaymentError(
                "You must specify a positive number of recurring extra payments", start_date, amount, count
            )
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        if amount <= 0:
            raise InvalidRecurringPaymentError(
                "Recurring extra payment amount must be positive amount", start_date, amount, count
            )
        self.recurring_extra_payments.append(RecurringExtraPayment(start_date=start_date, amount=amount, count=count))

    def _extras_for_scheduled_date(
        self, scheduled_dt: datetime.date
    ) -> list[tuple[PaymentKind, datetime.date, Decimal]]:
        extras: list[tuple[PaymentKind, datetime.date, Decimal]] = []

        for one_time in self.one_time_extra_payments:
            if one_time.date.year == scheduled_dt.year and one_time.date.month == scheduled_dt.month:
                extras.append((PaymentKind.OneTimeExtraPayment, one_time.date, one_time.amount))

        for recurring in self.recurring_extra_payments:
            dt = recurring.start_date
            for _ in range(recurring.count):
                if dt.year == scheduled_dt.year and dt.month == scheduled_dt.month:
                    extras.append((PaymentKind.RecurringExtraPayment, dt, recurring.amount))
                dt = next_month(dt)

        return sorted(extras, key=op.itemgetter(1))

    def generate(self, start_date: datetime.date) -> Generator[Installment]:
        current_balance = self.amount
        dt = start_date
        total_interest = Decimal("0.00")
        total_principal = Decimal("0.00")
        total_fees = Decimal("0.00")
        months_count = 0

        for i in range(1, self.periods + 1):
            interest = current_balance * self.monthly_interest_rate
            scheduled_principal = self.monthly_installment - interest
            if scheduled_principal < 0:
                scheduled_principal = Decimal("0.00")

            principal_payment = min(scheduled_principal, current_balance)
            balance_before = current_balance
            balance_after = balance_before - principal_payment

            scheduled_payment = Payment(
                kind=PaymentKind.ScheduledPayment,
                principal=principal_payment,
                interest=interest,
                fees=Decimal("0.00"),
            )
            month = Month(dt.month)
            yield Installment(
                i=i,
                year=dt.year,
                month=month,
                payment=scheduled_payment,
                balance=Balance(before=balance_before, after=balance_after),
            )

            total_interest += interest
            total_principal += principal_payment
            months_count = i
            current_balance = balance_after

            if current_balance <= Decimal("0.00"):
                dt = next_month(dt)
                break

            for kind, extra_dt, requested_amount in self._extras_for_scheduled_date(dt):
                payment_amount = min(requested_amount, current_balance)
                if payment_amount <= 0:
                    continue
                penalty = self.early_payment_fees.penalty(payment_amount)
                principal = self.early_payment_fees.principal(payment_amount)
                before = current_balance
                after = before - principal
                extra_payment = Payment(kind=kind, principal=principal, interest=Decimal("0.00"), fees=penalty)
                yield Installment(
                    i=None,
                    year=extra_dt.year,
                    month=Month(extra_dt.month),
                    payment=extra_payment,
                    balance=Balance(before=before, after=after),
                )
                total_principal += principal
                total_fees += penalty
                current_balance = after

            dt = next_month(dt)
            if current_balance <= Decimal("0.00"):
                break

        paid_off = current_balance <= Decimal("0.00")
        self._last_totals = ScheduleTotals(
            principal=total_principal,
            interest=total_interest,
            fees=total_fees,
            months=months_count,
            paid_off=paid_off,
        )
