import calendar
import datetime
import enum
from collections.abc import Generator
from dataclasses import dataclass
from decimal import Decimal

type Amount = int | float | Decimal
type TermType = int | tuple[int, int] | Term
type InterestRate = float | Decimal


_DAYS_IN_YEAR = Decimal("365")


class AmortizationError(Exception):
    pass


class InvalidTermError(AmortizationError):
    def __init__(self, message: str, term: Term) -> None:
        super().__init__(message)
        self.term = term


class InvalidExtraPaymentError(AmortizationError):
    def __init__(self, message: str, date: datetime.date, amount: Amount) -> None:
        super().__init__(message)
        self.date = date
        self.amount = amount


class InvalidRecurringPaymentError(AmortizationError):
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


def next_month(dt: datetime.date) -> datetime.date:
    year, month = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


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


class AmortizationSchedule:
    def __init__(
        self,
        amount: Amount,
        term: TermType,
        interest_rate: InterestRate,
        early_payment_fees: EarlyPaymentFees | None = None,
        *,
        interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth,
    ) -> None:
        self.amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        self.interest_rate = interest_rate if isinstance(interest_rate, Decimal) else Decimal(interest_rate)
        if isinstance(term, int):
            term = (term, 0)
        self.term = Term(*term) if isinstance(term, tuple) else term
        self.early_payment_fees = early_payment_fees if early_payment_fees is not None else EarlyPaymentFees()
        self.interest_rate_application = interest_rate_application

        # Variable-rate support (optional). If empty, the base self.interest_rate is used.
        self.interest_rate_changes: list[InterestRateChange] = []

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

    def add_interest_rate_change(self, effective_date: datetime.date, yearly_interest_rate: InterestRate) -> None:
        rate = yearly_interest_rate if isinstance(yearly_interest_rate, Decimal) else Decimal(yearly_interest_rate)
        if rate < 0:
            raise AmortizationError("Interest rate must be non-negative")
        self.interest_rate_changes.append(InterestRateChange(effective_date=effective_date, yearly_interest_rate=rate))
        self.interest_rate_changes.sort(key=lambda c: c.effective_date)

    def _yearly_rate_percent_for_date(self, dt: datetime.date) -> Decimal:
        # Latest change whose effective_date <= dt, otherwise fall back to base self.interest_rate.
        chosen: InterestRateChange | None = None
        for change in self.interest_rate_changes:
            if change.effective_date <= dt:
                chosen = change
            else:
                break
        return chosen.yearly_interest_rate if chosen is not None else self.interest_rate

    def _monthly_rate_for_date(self, dt: datetime.date) -> Decimal:
        yearly_percent = self._yearly_rate_percent_for_date(dt)
        yearly_fraction = yearly_percent / Decimal("100.00")
        return yearly_fraction / Decimal("12.00")

    def _daily_rate_for_date(self, dt: datetime.date) -> Decimal:
        yearly_percent = self._yearly_rate_percent_for_date(dt)
        yearly_fraction = yearly_percent / Decimal("100.00")
        return yearly_fraction / _DAYS_IN_YEAR

    def _daily_rate_for_date_with_application_limit(
        self,
        dt: datetime.date,
        *,
        scheduled_month_year: int,
        scheduled_month: int,
    ) -> Decimal:
        if self.interest_rate_application != InterestRateApplication.ProratedByDaysInMonth:
            return self._daily_rate_for_date(dt)

        # In ProratedByDaysInMonth mode, ignore rate changes that happen after the scheduled month.
        # This mirrors the original behavior where only changes inside the scheduled month were considered.
        days_in_month = calendar.monthrange(scheduled_month_year, scheduled_month)[1]
        last_day_of_scheduled_month = datetime.date(scheduled_month_year, scheduled_month, days_in_month)
        effective_dt = dt if dt <= last_day_of_scheduled_month else last_day_of_scheduled_month
        yearly_percent = self._yearly_rate_percent_for_date(effective_dt)
        yearly_fraction = yearly_percent / Decimal("100.00")
        return yearly_fraction / _DAYS_IN_YEAR

    def _extras_for_period(
        self,
        period_start: datetime.date,
        period_end: datetime.date,
    ) -> list[tuple[PaymentKind, datetime.date, Decimal]]:
        extras: list[tuple[PaymentKind, datetime.date, Decimal]] = []

        for one_time in self.one_time_extra_payments:
            if period_start <= one_time.date <= period_end:
                extras.append((PaymentKind.OneTimeExtraPayment, one_time.date, one_time.amount))

        for recurring in self.recurring_extra_payments:
            dt = recurring.start_date
            for _ in range(recurring.count):
                if period_start <= dt <= period_end:
                    extras.append((PaymentKind.RecurringExtraPayment, dt, recurring.amount))
                dt = next_month(dt)

        # Stable sort by date, then kind name for deterministic ordering.
        return sorted(extras, key=lambda x: (x[1], str(x[0])))

    def _rate_change_cut_points_for_period(
        self,
        period_start: datetime.date,
        period_end: datetime.date,
    ) -> set[datetime.date]:
        if self.interest_rate_application == InterestRateApplication.WholeMonth:
            return set()

        if self.interest_rate_application == InterestRateApplication.ProratedByDaysInMonth:
            scheduled_year, scheduled_month = period_start.year, period_start.month
            return {
                c.effective_date
                for c in self.interest_rate_changes
                if (
                    c.effective_date.year == scheduled_year
                    and c.effective_date.month == scheduled_month
                    and period_start < c.effective_date < period_end
                )
            }

        # ProratedByPaymentPeriod
        return {c.effective_date for c in self.interest_rate_changes if period_start < c.effective_date < period_end}

    def _split_extras_for_period_end(
        self,
        *,
        extras: list[tuple[PaymentKind, datetime.date, Decimal]],
        period_end: datetime.date,
    ) -> tuple[
        dict[datetime.date, list[tuple[PaymentKind, Decimal]]],
        list[tuple[PaymentKind, datetime.date, Decimal]],
    ]:
        extras_by_date: dict[datetime.date, list[tuple[PaymentKind, Decimal]]] = {}
        extras_on_end: list[tuple[PaymentKind, datetime.date, Decimal]] = []

        for kind, dt, amount in extras:
            if dt == period_end:
                extras_on_end.append((kind, dt, amount))
                continue
            if dt < period_end:
                extras_by_date.setdefault(dt, []).append((kind, amount))

        return extras_by_date, extras_on_end

    def _apply_extra_payment(
        self,
        *,
        kind: PaymentKind,
        dt: datetime.date,
        requested_amount: Decimal,
        balance: Decimal,
    ) -> tuple[Installment | None, Decimal]:
        if balance <= Decimal("0.00"):
            return None, balance

        payment_amount = min(requested_amount, balance)
        if payment_amount <= 0:
            return None, balance

        penalty = self.early_payment_fees.penalty(payment_amount)
        principal = self.early_payment_fees.principal(payment_amount)
        before = balance
        after = before - principal
        extra_payment = Payment(kind=kind, principal=principal, interest=Decimal("0.00"), fees=penalty)
        row = Installment(
            i=None,
            year=dt.year,
            month=Month(dt.month),
            payment=extra_payment,
            balance=Balance(before=before, after=after),
        )
        return row, after

    def _daily_rate_for_segment(self, *, period_start: datetime.date, segment_start: datetime.date) -> Decimal:
        if self.interest_rate_application == InterestRateApplication.WholeMonth:
            return self._daily_rate_for_date(period_start)

        return self._daily_rate_for_date_with_application_limit(
            segment_start,
            scheduled_month_year=period_start.year,
            scheduled_month=period_start.month,
        )

    def _accrue_interest_and_apply_extras(
        self,
        *,
        starting_balance: Decimal,
        period_start: datetime.date,
        period_end: datetime.date,
        extras: list[tuple[PaymentKind, datetime.date, Decimal]],
    ) -> tuple[
        Decimal,
        Decimal,
        list[Installment],
        list[tuple[PaymentKind, datetime.date, Decimal]],
    ]:
        """Accrue daily interest over [period_start, period_end) and apply extras as principal curtailments.

        Returns:
        - total interest accrued over the period
        - balance at period_end (before scheduled payment)
        - extra installments that occurred before period_end (chronological)
        - extra installments that occurred exactly on period_end (chronological)
        """

        extras_by_date, extras_on_end = self._split_extras_for_period_end(extras=extras, period_end=period_end)

        extra_installments_before_end: list[Installment] = []

        # Build cut points from period boundaries, relevant rate changes, and extra payment dates.
        cut_points: set[datetime.date] = {period_start, period_end}
        cut_points |= self._rate_change_cut_points_for_period(period_start, period_end)
        cut_points |= set(extras_by_date.keys())
        points = sorted(cut_points)

        balance = starting_balance
        interest = Decimal("0.00")

        for idx, seg_start in enumerate(points[:-1]):
            seg_end = points[idx + 1]
            for kind, requested_amount in extras_by_date.get(seg_start, []):
                row, balance = self._apply_extra_payment(
                    kind=kind,
                    dt=seg_start,
                    requested_amount=requested_amount,
                    balance=balance,
                )
                if row is not None:
                    extra_installments_before_end.append(row)

            if balance <= Decimal("0.00"):
                continue

            days = (seg_end - seg_start).days
            if days <= 0:
                continue

            daily_rate = self._daily_rate_for_segment(period_start=period_start, segment_start=seg_start)
            interest += balance * daily_rate * Decimal(days)

        return interest, balance, extra_installments_before_end, extras_on_end

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

    def generate(self, start_date: datetime.date) -> Generator[Installment]:
        current_balance = self.amount
        period_start = start_date
        total_interest = Decimal("0.00")
        total_principal = Decimal("0.00")
        total_fees = Decimal("0.00")
        months_count = 0

        for i in range(1, self.periods + 1):
            period_end = next_month(period_start)

            extras = self._extras_for_period(period_start, period_end)

            (
                interest,
                balance_before_scheduled,
                extra_rows_before_end,
                extras_on_end,
            ) = self._accrue_interest_and_apply_extras(
                starting_balance=current_balance,
                period_start=period_start,
                period_end=period_end,
                extras=extras,
            )

            # Emit extra payments that occur during the period (chronological).
            for row in extra_rows_before_end:
                yield row
                total_principal += row.payment.principal
                total_fees += row.payment.fees

            current_balance = balance_before_scheduled
            if current_balance <= Decimal("0.00"):
                # Paid off via extra payments before the scheduled payment date.
                period_start = period_end
                break

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
            yield Installment(
                i=i,
                year=period_end.year,
                month=Month(period_end.month),
                payment=scheduled_payment,
                balance=Balance(before=balance_before, after=balance_after),
            )

            total_interest += interest
            total_principal += principal_payment
            months_count = i
            current_balance = balance_after

            if current_balance <= Decimal("0.00"):
                period_start = period_end
                break

            # Apply any extras that happen exactly on period_end after the scheduled payment.
            for kind, extra_dt, requested_amount in extras_on_end:
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

            period_start = period_end
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
