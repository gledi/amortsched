import datetime
from decimal import Decimal

import pytest

from amortsched.amortization import (
    AmortizationError,
    AmortizationSchedule,
    EarlyPaymentFees,
    InterestRateApplication,
    PaymentKind,
)


def _first_scheduled_payment(schedule: AmortizationSchedule, *, start_date: datetime.date):
    rows = list(schedule.generate(start_date=start_date))
    return next(r for r in rows if r.payment.kind == PaymentKind.ScheduledPayment)


def test_amortization_schedule_without_extra_payments() -> None:
    schedule = AmortizationSchedule(amount=1000, term=1, interest_rate=10)

    start = datetime.date(2025, 1, 5)
    rows = list(schedule.generate(start_date=start))
    scheduled = [r for r in rows if r.payment.kind == PaymentKind.ScheduledPayment]

    # With daily accrual, interest (and thus principal) varies by period length, so don't assert fixed totals.
    assert len(scheduled) == 12
    assert schedule.last_totals is not None
    assert schedule.last_totals.fees == Decimal("0.00")
    assert schedule.last_totals.principal == pytest.approx(Decimal("1000"))
    assert schedule.last_totals.interest > Decimal("0.00")

    # Totals should match what was emitted.
    assert sum(r.payment.total for r in rows) == pytest.approx(schedule.last_totals.total_outflow)


def test_one_time_extra_payment_reduces_balance_and_has_no_installment_number() -> None:
    early_fees = EarlyPaymentFees(fixed=5, percent=1)
    schedule = AmortizationSchedule(amount=1000, term=1, interest_rate=10, early_payment_fees=early_fees)

    start = datetime.date(2025, 1, 5)
    schedule.add_one_time_extra_payment(datetime.date(2025, 1, 15), 200)

    rows = list(schedule.generate(start_date=start))

    extra_rows = [r for r in rows if r.payment.kind == PaymentKind.OneTimeExtraPayment]
    assert len(extra_rows) == 1
    assert extra_rows[0].i is None

    scheduled_rows = [r for r in rows if r.payment.kind == PaymentKind.ScheduledPayment]
    assert scheduled_rows[0].i == 1

    # Balance decreases by the *principal portion* of the extra payment.
    assert extra_rows[0].balance.after == extra_rows[0].balance.before - extra_rows[0].payment.principal

    requested_amount = Decimal("200")
    expected_fee = Decimal("5") + (Decimal("1") / Decimal("100")) * requested_amount
    assert extra_rows[0].payment.fees == expected_fee
    assert extra_rows[0].payment.principal == requested_amount - expected_fee


def test_recurring_extra_payments_apply_count_times() -> None:
    schedule = AmortizationSchedule(amount=1000, term=1, interest_rate=10)

    start = datetime.date(2025, 1, 7)
    schedule.add_recurring_extra_payment(start_date=datetime.date(2025, 2, 1), amount=50, count=3)

    rows = list(schedule.generate(start_date=start))
    recurring_rows = [r for r in rows if r.payment.kind == PaymentKind.RecurringExtraPayment]

    assert len(recurring_rows) == 3
    assert all(r.i is None for r in recurring_rows)


def test_interest_rate_change_whole_month_uses_rate_effective_at_scheduled_date() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.WholeMonth,
    )

    start = datetime.date(2025, 1, 1)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 16), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)

    # WholeMonth: apply the rate effective as-of the period start (Jan 1 => 12%) to every day in the period.
    days = Decimal("31")
    daily = (Decimal("12") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily * days
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_interest_rate_change_prorated_by_payment_period_splits_interest_by_days() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )

    start = datetime.date(2025, 1, 1)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 16), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)

    # Daily accrual across [2025-01-01, 2025-02-01):
    # - 15 days at 12% yearly
    # - 16 days at 24% yearly
    days_old = Decimal("15")
    days_new = Decimal("16")
    daily_old = (Decimal("12") / Decimal("100")) / Decimal("365")
    daily_new = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily_old * days_old + Decimal("1000") * daily_new * days_new
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_interest_rate_change_on_period_end_does_not_affect_current_period_proration() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )

    start = datetime.date(2025, 1, 1)
    # Effective exactly at the end of the payment period; should apply to the next installment.
    schedule.add_interest_rate_change(datetime.date(2025, 2, 1), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    days = Decimal("31")
    daily = (Decimal("12") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily * days
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_prorated_by_payment_period_handles_end_of_month_day_clamp() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )

    start = datetime.date(2025, 1, 31)
    # next_month(2025-01-31) -> 2025-02-28 (clamped)
    schedule.add_interest_rate_change(datetime.date(2025, 2, 1), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)

    # Daily accrual across [2025-01-31, 2025-02-28):
    # - 1 day at 12% yearly
    # - 27 days at 24% yearly
    days_old = Decimal("1")
    days_new = Decimal("27")
    daily_old = (Decimal("12") / Decimal("100")) / Decimal("365")
    daily_new = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily_old * days_old + Decimal("1000") * daily_new * days_new
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_prorated_by_days_in_month_ignores_next_month_rate_change_within_payment_period() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByDaysInMonth,
    )
    start = datetime.date(2025, 1, 31)
    schedule.add_interest_rate_change(datetime.date(2025, 2, 1), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    # Change is in Feb, scheduled month is Jan => ignored.
    days = Decimal("28")
    daily = (Decimal("12") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily * days
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_prorated_by_days_in_month_includes_changes_within_scheduled_month() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByDaysInMonth,
    )
    start = datetime.date(2025, 1, 1)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 16), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    days_old = Decimal("15")
    days_new = Decimal("16")
    daily_old = (Decimal("12") / Decimal("100")) / Decimal("365")
    daily_new = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily_old * days_old + Decimal("1000") * daily_new * days_new
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_multiple_rate_changes_within_payment_period_split_into_three_segments() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )
    start = datetime.date(2025, 1, 1)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 10), 18)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 20), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    days_a = Decimal("9")
    days_b = Decimal("10")
    days_c = Decimal("12")
    da = (Decimal("12") / Decimal("100")) / Decimal("365")
    db = (Decimal("18") / Decimal("100")) / Decimal("365")
    dc = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * da * days_a + Decimal("1000") * db * days_b + Decimal("1000") * dc * days_c
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_rate_change_effective_on_period_start_applies_immediately() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )
    start = datetime.date(2025, 1, 1)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 1), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    days = Decimal("31")
    daily = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily * days
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_rate_change_before_start_date_is_in_effect_for_first_period() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.WholeMonth,
    )
    schedule.add_interest_rate_change(datetime.date(2024, 12, 15), 24)
    start = datetime.date(2025, 1, 1)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    days = Decimal("31")
    daily = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily * days
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_duplicate_effective_dates_use_last_declared_rate() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )
    start = datetime.date(2025, 1, 1)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 15), 18)
    schedule.add_interest_rate_change(datetime.date(2025, 1, 15), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    days_old = Decimal("14")
    days_new = Decimal("17")
    daily_old = (Decimal("12") / Decimal("100")) / Decimal("365")
    daily_new = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily_old * days_old + Decimal("1000") * daily_new * days_new
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_negative_interest_rate_change_raises() -> None:
    schedule = AmortizationSchedule(amount=1000, term=1, interest_rate=10)
    with pytest.raises(AmortizationError):
        schedule.add_interest_rate_change(datetime.date(2025, 1, 1), -1)


def test_prorated_by_payment_period_handles_leap_year_february_day_clamp() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=12,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )
    start = datetime.date(2024, 1, 31)
    # next_month(2024-01-31) -> 2024-02-29
    schedule.add_interest_rate_change(datetime.date(2024, 2, 1), 24)

    first_scheduled = _first_scheduled_payment(schedule, start_date=start)
    days_old = Decimal("1")
    days_new = Decimal("28")
    daily_old = (Decimal("12") / Decimal("100")) / Decimal("365")
    daily_new = (Decimal("24") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily_old * days_old + Decimal("1000") * daily_new * days_new
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)


def test_extra_payment_mid_period_reduces_daily_accrued_interest() -> None:
    schedule = AmortizationSchedule(
        amount=1000,
        term=1,
        interest_rate=36,
        interest_rate_application=InterestRateApplication.WholeMonth,
    )
    start = datetime.date(2025, 1, 1)
    schedule.add_one_time_extra_payment(datetime.date(2025, 1, 16), 500)

    rows = list(schedule.generate(start_date=start))
    assert any(r.payment.kind == PaymentKind.OneTimeExtraPayment for r in rows)
    first_scheduled = [r for r in rows if r.payment.kind == PaymentKind.ScheduledPayment][0]

    # Interest accrues on 1000 until Jan 16, then on 500 for the remainder of the period.
    days_full = Decimal("15")
    days_reduced = Decimal("16")
    daily = (Decimal("36") / Decimal("100")) / Decimal("365")
    expected_interest = Decimal("1000") * daily * days_full + Decimal("500") * daily * days_reduced
    assert first_scheduled.payment.interest == pytest.approx(expected_interest)
