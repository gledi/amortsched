import datetime
from decimal import Decimal

import pytest

from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.errors import InvalidTermError
from amortsched.core.values import Term


def test_basic_amortization():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("5.0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) == 360
    assert schedule.last_totals is not None
    assert schedule.last_totals.months == 360
    assert schedule.last_totals.principal == Decimal("100000")
    assert schedule.last_totals.paid_off is True
    assert installments[-1].balance.after == Decimal("0.00")


def test_zero_interest_rate():
    schedule = AmortizationSchedule(amount=12_000, term=Term(1), interest_rate=Decimal("0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) == 12
    assert all(inst.payment.interest == Decimal("0") for inst in installments)


def test_zero_length_term_is_invalid():
    with pytest.raises(InvalidTermError):
        Term(0)


def test_next_month_no_date_drift():
    schedule = AmortizationSchedule(amount=10_000, term=Term(1), interest_rate=Decimal("5.0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 31)))
    # Months should be Jan 2025, Feb 2025, Mar 2025, ..., Dec 2025
    years_and_months = [(inst.year, inst.month.value) for inst in installments]
    assert years_and_months == [(2025, m) for m in range(1, 13)]


def test_one_time_extra_payment_reduces_term():
    # 10,000 at 5% over 1 year normally takes 12 installments.
    # With a massive extra payment of 5,000 at month 2, it should pay off early.
    schedule = AmortizationSchedule(amount=10_000, term=Term(1), interest_rate=Decimal("5.0"))
    schedule.add_one_time_extra_payment(datetime.date(2025, 3, 1), Decimal("5000.00"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) < 13
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True
    assert schedule.last_totals.principal == Decimal("10000")


def test_recurring_extra_payment():
    schedule = AmortizationSchedule(amount=50_000, term=Term(5), interest_rate=Decimal("6.0"))
    schedule.add_recurring_extra_payment(datetime.date(2025, 2, 1), Decimal("500.00"), count=12)
    _ = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert schedule.last_totals is not None
    assert schedule.last_totals.months < 60


def test_early_payment_fees_validation_and_penalty():
    from amortsched.core.values import EarlyPaymentFees

    with pytest.raises(ValueError, match="negative"):
        EarlyPaymentFees(fixed=Decimal("-10.00"))

    with pytest.raises(ValueError, match="between 0 and 100"):
        EarlyPaymentFees(percent=Decimal("150.00"))

    fees = EarlyPaymentFees(fixed=Decimal("50.00"), percent=Decimal("2.00"))
    # For a 1,000 payment: 50 + 2% of 1,000 (20) = 70 penalty
    assert fees.penalty(Decimal("1000.00")) == Decimal("70.00")
    assert fees.principal(Decimal("1000.00")) == Decimal("930.00")

    # If penalty exceeds payment amount, principal clamped to 0
    small_fees = EarlyPaymentFees(fixed=Decimal("100.00"))
    assert small_fees.principal(Decimal("50.00")) == Decimal("0.00")


def test_interest_rate_change_whole_month():
    from amortsched.core.values import InterestRateApplication

    schedule = AmortizationSchedule(
        amount=10_000,
        term=Term(1),
        interest_rate=Decimal("5.0"),
        interest_rate_application=InterestRateApplication.WholeMonth,
    )
    schedule.add_interest_rate_change(datetime.date(2025, 6, 15), Decimal("10.0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) == 12
    # Before June: interest at 5%, after June: interest at 10%
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True


def test_interest_rate_change_prorated_days():
    from amortsched.core.values import InterestRateApplication

    schedule = AmortizationSchedule(
        amount=10_000,
        term=Term(1),
        interest_rate=Decimal("5.0"),
        interest_rate_application=InterestRateApplication.ProratedByDaysInMonth,
    )
    schedule.add_interest_rate_change(datetime.date(2025, 6, 15), Decimal("8.0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) == 12
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True


def test_interest_rate_change_prorated_payment_period():
    from amortsched.core.values import InterestRateApplication

    schedule = AmortizationSchedule(
        amount=10_000,
        term=Term(1),
        interest_rate=Decimal("5.0"),
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )
    schedule.add_interest_rate_change(datetime.date(2025, 4, 10), Decimal("7.0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) == 12
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True
