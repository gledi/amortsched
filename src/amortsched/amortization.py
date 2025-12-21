import calendar
import datetime
import enum
from collections.abc import Generator
from dataclasses import dataclass
from decimal import Decimal

type TermType = int | tuple[int, int] | Term

type InterestRate = float | Decimal


class InvalidTermError(Exception):
    def __init__(self, message, term: Term) -> None:
        super().__init__(message)
        self.term = term


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
class Payment:
    principal: Decimal
    interest: Decimal

    @property
    def installment(self) -> Decimal:
        return self.principal + self.interest


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
    i: int
    year: int
    month: Month
    payment: Payment
    balance: Balance

    @property
    def month_name(self) -> str:
        return self.month.name

    def to_row(self) -> list[str]:
        return [
            str(self.i),
            f"{self.year}/{self.month.name}",
            f"{self.payment.principal:,.2f}",
            f"{self.payment.interest:,.2f}",
            f"{self.payment.installment:,.2f}",
            f"{self.balance.before:,.2f}",
            f"{self.balance.after:,.2f}",
        ]


class Periodicity(enum.Enum):
    Monthly = "monthly"
    Yearly = "yearly"


def next_month(dt: datetime.date) -> datetime.date:
    year, month = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


class AmortizationSchedule:
    def __init__(
        self,
        amount: int | float | Decimal,
        term: TermType,
        interest_rate: InterestRate,
    ):
        self.amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        self.interest_rate = interest_rate if isinstance(interest_rate, Decimal) else Decimal(interest_rate)
        if isinstance(term, int):
            term = (term, 0)
        self.term = Term(*term) if isinstance(term, tuple) else term
        self.extra_payments: dict[datetime.date, Decimal] = {}

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
        return ((1 + rate) ** self.periods - 1) / (rate * (1 + rate) ** self.periods)

    @property
    def monthly_installment(self) -> Decimal:
        return self.amount / self.discount_factor

    @property
    def total_amount_paid(self) -> Decimal:
        return self.monthly_installment * self.periods

    @property
    def total_interest_paid(self) -> Decimal:
        return self.total_amount_paid - self.amount

    def add_extra_payment(self, dt: datetime.date, amount: int | float | Decimal) -> None:
        amt = amount if isinstance(amount, Decimal) else Decimal(amount)
        if dt in self.extra_payments:
            self.extra_payments[dt] += amt
        else:
            self.extra_payments[dt] = amt

    def generate(self, start_date: datetime.date) -> Generator[Installment]:
        current_balance = self.amount
        dt = start_date
        for i in range(1, self.periods + 1):
            interest = current_balance * self.monthly_interest_rate
            principal = self.monthly_installment - interest

            balance_before = current_balance
            balance_after = current_balance - principal
            current_balance = balance_after
            balance = Balance(before=balance_before, after=balance_after)
            payment = Payment(principal=principal, interest=interest)
            month = Month(dt.month)
            installment = Installment(i=i, year=dt.year, month=month, payment=payment, balance=balance)
            yield installment
            dt = next_month(dt)
            if current_balance <= Decimal("0.00"):
                break
