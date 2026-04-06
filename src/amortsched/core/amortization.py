import calendar
import datetime
from collections.abc import Generator
from decimal import Decimal

from amortsched.core.errors import AmortizationError, InvalidExtraPaymentError, InvalidRecurringPaymentError
from amortsched.core.values import (
    _DAYS_IN_YEAR,
    Amount,
    Balance,
    EarlyPaymentFees,
    Installment,
    InterestRate,
    InterestRateApplication,
    InterestRateChange,
    Month,
    OneTimeExtraPayment,
    Payment,
    PaymentKind,
    RecurringExtraPayment,
    ScheduleTotals,
    Term,
    TermType,
)


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
        period_start: datetime.date,
        period_end: datetime.date,
        balance: Decimal,
    ) -> tuple[list[Installment], Decimal, Decimal]:
        extras = self._extras_for_period(period_start, period_end)
        extras_by_date, extras_on_end = self._split_extras_for_period_end(extras=extras, period_end=period_end)

        cut_points = set(extras_by_date.keys()) | self._rate_change_cut_points_for_period(period_start, period_end)
        cut_points = {dt for dt in cut_points if period_start < dt < period_end}

        segment_starts = [period_start] + sorted(cut_points)
        segment_starts.append(period_end)

        installments: list[Installment] = []
        interest_total = Decimal("0.00")
        for i in range(len(segment_starts) - 1):
            segment_start = segment_starts[i]
            segment_end = segment_starts[i + 1]
            days = (segment_end - segment_start).days
            if days <= 0:
                continue
            rate = self._daily_rate_for_segment(period_start=period_start, segment_start=segment_start)
            interest = balance * rate * Decimal(days)
            interest_total += interest

            if segment_start in extras_by_date:
                for kind, amount in extras_by_date[segment_start]:
                    extra_row, balance = self._apply_extra_payment(
                        kind=kind,
                        dt=segment_start,
                        requested_amount=amount,
                        balance=balance,
                    )
                    if extra_row:
                        installments.append(extra_row)

        for kind, dt, amount in extras_on_end:
            extra_row, balance = self._apply_extra_payment(
                kind=kind,
                dt=dt,
                requested_amount=amount,
                balance=balance,
            )
            if extra_row:
                installments.append(extra_row)

        return installments, balance, interest_total

    def _validate_one_time_extra_payment(self, date: datetime.date, amount: Decimal) -> None:
        if amount <= 0:
            raise InvalidExtraPaymentError("Extra payment amount must be positive", date, amount)

    def _validate_recurring_extra_payment(self, start_date: datetime.date, amount: Decimal, count: int) -> None:
        if amount <= 0:
            raise InvalidRecurringPaymentError("Recurring payment amount must be positive", start_date, amount, count)
        if count <= 0:
            raise InvalidRecurringPaymentError("Recurring payment count must be positive", start_date, amount, count)

    def add_one_time_extra_payment(self, date: datetime.date, amount: Amount) -> None:
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        self._validate_one_time_extra_payment(date, amount)
        self.one_time_extra_payments.append(OneTimeExtraPayment(date=date, amount=amount))

    def add_recurring_extra_payment(self, start_date: datetime.date, amount: Amount, count: int) -> None:
        amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        self._validate_recurring_extra_payment(start_date, amount, count)
        self.recurring_extra_payments.append(RecurringExtraPayment(start_date=start_date, amount=amount, count=count))

    def generate(self, start_date: datetime.date) -> Generator[Installment, None, None]:
        balance = self.amount
        date = start_date
        scheduled_payment_index = 0
        total_principal = Decimal("0.00")
        total_interest = Decimal("0.00")
        total_fees = Decimal("0.00")
        paid_off = False

        while balance > 0 and scheduled_payment_index < self.periods:
            period_start = date
            period_end = next_month(date)

            extras, balance, accrued_interest = self._accrue_interest_and_apply_extras(
                period_start=period_start,
                period_end=period_end,
                balance=balance,
            )
            for extra in extras:
                total_principal += extra.payment.principal
                total_fees += extra.payment.fees
                yield extra

            if balance <= Decimal("0.00"):
                total_interest += accrued_interest
                paid_off = True
                break

            scheduled_payment_index += 1
            principal = self.monthly_installment - accrued_interest
            if principal > balance:
                principal = balance
            scheduled = Payment(
                kind=PaymentKind.ScheduledPayment,
                principal=principal,
                interest=accrued_interest,
                fees=Decimal("0.00"),
            )
            before = balance
            balance = before - scheduled.principal
            after = max(balance, Decimal("0.00"))

            if balance <= Decimal("0.00"):
                scheduled.principal = before
                balance = Decimal("0.00")
                paid_off = True

            total_principal += scheduled.principal
            total_interest += scheduled.interest
            total_fees += scheduled.fees

            yield Installment(
                i=scheduled_payment_index,
                year=period_start.year,
                month=Month(period_start.month),
                payment=scheduled,
                balance=Balance(before=before, after=after),
            )

            date = period_end

        self._last_totals = ScheduleTotals(
            principal=total_principal,
            interest=total_interest,
            fees=total_fees,
            months=scheduled_payment_index,
            paid_off=paid_off,
        )
