import calendar
import datetime
from collections.abc import Generator
from decimal import Decimal
from typing import override

from amortsched.core.errors import AmortizationError, InvalidExtraPaymentError, InvalidRecurringPaymentError
from amortsched.core.money import HUNDRED, ZERO, round_cents
from amortsched.core.payments import monthly_payment
from amortsched.core.values import (
    DAYS_IN_YEAR,
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


def next_month(dt: datetime.date, base_day: int | None = None) -> datetime.date:
    year, month = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    target_day = base_day if base_day is not None else dt.day
    day = min(target_day, calendar.monthrange(year, month)[1])
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
        self.amount: Decimal = amount if isinstance(amount, Decimal) else Decimal(amount)
        self.interest_rate: Decimal = interest_rate if isinstance(interest_rate, Decimal) else Decimal(interest_rate)
        if isinstance(term, int):
            term = (term, 0)
        self.term: Term = Term(*term) if isinstance(term, tuple) else term
        self.early_payment_fees: EarlyPaymentFees = (
            early_payment_fees if early_payment_fees is not None else EarlyPaymentFees()
        )
        self.interest_rate_application: InterestRateApplication = interest_rate_application

        self.interest_rate_changes: list[InterestRateChange] = []

        self.one_time_extra_payments: list[OneTimeExtraPayment] = []
        self.recurring_extra_payments: list[RecurringExtraPayment] = []
        self._last_totals: ScheduleTotals | None = None

    @override
    def __str__(self) -> str:
        term_parts = [f"{self.term.years} years"]
        if self.term.months > 0:
            term_parts.append(f"{self.term.months} months")
        term = " and ".join(term_parts)
        return f"{self.amount:,.2f} over {term} at {self.interest_rate:.2f}% yearly interest rate"

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(amount={self.amount:_.2f}, term={self.term!r}, "
            f"interest_rate={self.interest_rate!r})"
        )

    @property
    def yearly_interest_rate(self) -> Decimal:
        return self.interest_rate / HUNDRED

    @property
    def monthly_interest_rate(self) -> Decimal:
        return self.yearly_interest_rate / Decimal("12.00")

    @property
    def periods(self) -> int:
        return self.term.periods

    def starting_payment(self, start_date: datetime.date) -> Decimal:
        return monthly_payment(self.amount, self._yearly_rate_percent_for_date(start_date), self.periods)

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

    def _yearly_rate_percent_with_application_limit(
        self,
        dt: datetime.date,
        *,
        scheduled_month_year: int,
        scheduled_month: int,
    ) -> Decimal:
        if self.interest_rate_application != InterestRateApplication.ProratedByDaysInMonth:
            return self._yearly_rate_percent_for_date(dt)

        # In ProratedByDaysInMonth mode, ignore rate changes that happen after the scheduled month.
        # This mirrors the original behavior where only changes inside the scheduled month were considered.
        days_in_month = calendar.monthrange(scheduled_month_year, scheduled_month)[1]
        last_day_of_scheduled_month = datetime.date(scheduled_month_year, scheduled_month, days_in_month)
        effective_dt = dt if dt <= last_day_of_scheduled_month else last_day_of_scheduled_month
        return self._yearly_rate_percent_for_date(effective_dt)

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
            base_day = recurring.start_date.day
            for _ in range(recurring.count):
                if period_start <= dt <= period_end:
                    extras.append((PaymentKind.RecurringExtraPayment, dt, recurring.amount))
                dt = next_month(dt, base_day=base_day)

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
        if balance <= ZERO:
            return None, balance

        payment_amount = min(requested_amount, balance)
        if payment_amount <= 0:
            return None, balance

        penalty = self.early_payment_fees.penalty(payment_amount)
        principal = self.early_payment_fees.principal(payment_amount)
        before = balance
        after = before - principal
        extra_payment = Payment(kind=kind, principal=principal, interest=ZERO, fees=penalty)
        row = Installment(
            i=None,
            year=dt.year,
            month=Month(dt.month),
            payment=extra_payment,
            balance=Balance(before=before, after=after),
        )
        return row, after

    def _yearly_rate_percent_for_segment(
        self,
        *,
        period_start: datetime.date,
        segment_start: datetime.date,
    ) -> Decimal:
        if self.interest_rate_application == InterestRateApplication.WholeMonth:
            return self._yearly_rate_percent_for_date(period_start)

        return self._yearly_rate_percent_with_application_limit(
            segment_start,
            scheduled_month_year=period_start.year,
            scheduled_month=period_start.month,
        )

    def _interest_day_basis(self, *, period_start: datetime.date, period_end: datetime.date) -> Decimal:
        if self.interest_rate_application == InterestRateApplication.WholeMonth:
            return Decimal(12 * (period_end - period_start).days)
        return DAYS_IN_YEAR

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
        interest_numerator = ZERO
        for i in range(len(segment_starts) - 1):
            segment_start = segment_starts[i]
            segment_end = segment_starts[i + 1]
            days = (segment_end - segment_start).days
            if days <= 0:
                continue
            rate = self._yearly_rate_percent_for_segment(period_start=period_start, segment_start=segment_start)
            interest_numerator += balance * rate * days

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

        day_basis = self._interest_day_basis(period_start=period_start, period_end=period_end)
        interest = round_cents(interest_numerator / (HUNDRED * day_basis))
        return installments, balance, interest

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
        base_day = start_date.day
        scheduled_payment_index = 0
        total_principal = ZERO
        total_interest = ZERO
        total_fees = ZERO
        paid_off = False
        payment_rate = self._yearly_rate_percent_for_date(start_date)
        scheduled_amount = self.starting_payment(start_date)

        while balance > 0 and scheduled_payment_index < self.periods:
            period_start = date
            period_end = next_month(date, base_day=base_day)

            period_rate = self._yearly_rate_percent_for_date(period_start)
            if period_rate != payment_rate:
                payment_rate = period_rate
                scheduled_amount = monthly_payment(balance, payment_rate, self.periods - scheduled_payment_index)

            extras, balance, accrued_interest = self._accrue_interest_and_apply_extras(
                period_start=period_start,
                period_end=period_end,
                balance=balance,
            )
            paid_off_by_extras = balance <= ZERO
            if paid_off_by_extras:
                extras[-1].payment.interest = accrued_interest
            for extra in extras:
                total_principal += extra.payment.principal
                total_interest += extra.payment.interest
                total_fees += extra.payment.fees
                yield extra

            if paid_off_by_extras:
                paid_off = True
                break

            scheduled_payment_index += 1
            principal = scheduled_amount - accrued_interest
            if scheduled_payment_index == self.periods:
                principal = balance
            if principal > balance:
                principal = balance
            scheduled = Payment(
                kind=PaymentKind.ScheduledPayment,
                principal=principal,
                interest=accrued_interest,
                fees=ZERO,
            )
            before = balance
            balance = before - scheduled.principal
            after = max(balance, ZERO)

            if balance <= ZERO:
                scheduled.principal = before
                balance = ZERO
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

        if paid_off:
            total_principal = self.amount

        self._last_totals = ScheduleTotals(
            principal=total_principal,
            interest=total_interest,
            fees=total_fees,
            months=scheduled_payment_index,
            paid_off=paid_off,
        )
