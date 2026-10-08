import datetime
from decimal import Decimal

import pytest

from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.errors import InvalidTermError
from amortsched.core.values import InterestRateApplication, Term


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


CENT = Decimal("0.01")


def scheduled_payments(installments):
    return [inst.payment.total.quantize(CENT) for inst in installments if inst.i is not None]


def test_rate_change_recalculates_payment_reg_z_example_a():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("9"))
    schedule.add_interest_rate_change(datetime.date(2026, 1, 1), Decimal("12"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    payments = scheduled_payments(installments)
    assert len(payments) == 360
    assert payments[:12] == [Decimal("804.62")] * 12
    assert payments[12:359] == [Decimal("1025.31")] * 347
    assert payments[359] < Decimal("1025.31") * 2
    assert installments[-1].balance.after == Decimal("0")
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True


def test_each_rate_change_recalculates_payment_reg_z_example_b():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("9"))
    schedule.add_interest_rate_change(datetime.date(2026, 1, 1), Decimal("11"))
    schedule.add_interest_rate_change(datetime.date(2027, 1, 1), Decimal("12"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    payments = scheduled_payments(installments)
    assert len(payments) == 360
    assert payments[:12] == [Decimal("804.62")] * 12
    assert payments[12:24] == [Decimal("950.09")] * 12
    assert payments[24:359] == [Decimal("1024.34")] * 335
    assert installments[-1].balance.after == Decimal("0")


def test_rate_decrease_lowers_payment():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("12"))
    schedule.add_interest_rate_change(datetime.date(2026, 1, 1), Decimal("9"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    payments = scheduled_payments(installments)
    assert len(payments) == 360
    assert payments[0] == Decimal("1028.61")
    assert payments[12] < payments[11]
    assert len(set(payments[12:359])) == 1
    assert installments[-1].balance.after == Decimal("0")


def test_rate_change_to_zero_spreads_remaining_balance_evenly():
    schedule = AmortizationSchedule(amount=12_000, term=Term(2), interest_rate=Decimal("6"))
    schedule.add_interest_rate_change(datetime.date(2026, 1, 1), Decimal("0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    zero_rate_rows = [inst for inst in installments if inst.i is not None and inst.i > 12]
    assert len(zero_rate_rows) == 12
    assert all(inst.payment.interest == 0 for inst in zero_rate_rows)
    expected = (zero_rate_rows[0].balance.before / 12).quantize(CENT)
    assert {inst.payment.total.quantize(CENT) for inst in zero_rate_rows} == {expected}
    assert installments[-1].balance.after == Decimal("0")
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True
    assert schedule.last_totals.months == 24


@pytest.mark.parametrize("effective_date", [datetime.date(2024, 6, 1), datetime.date(2025, 1, 1)])
def test_rate_change_on_or_before_start_sets_starting_payment(effective_date):
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("5"))
    schedule.add_interest_rate_change(effective_date, Decimal("9"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    payments = scheduled_payments(installments)
    assert payments[:359] == [Decimal("804.62")] * 359
    assert schedule.starting_payment(datetime.date(2025, 1, 1)).quantize(CENT) == Decimal("804.62")
    assert installments[-1].balance.after == Decimal("0")


def test_extra_payment_on_fixed_rate_plan_keeps_payment_and_shortens_term():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("9"))
    schedule.add_one_time_extra_payment(datetime.date(2025, 6, 15), Decimal("10000"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    payments = scheduled_payments(installments)
    assert len(payments) < 360
    assert payments[:-1] == [Decimal("804.62")] * (len(payments) - 1)
    assert installments[-1].balance.after == Decimal("0")
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True


def test_extra_payment_before_rate_change_lowers_recalculated_payment_and_keeps_maturity():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("9"))
    schedule.add_interest_rate_change(datetime.date(2026, 1, 1), Decimal("12"))
    schedule.add_one_time_extra_payment(datetime.date(2025, 6, 15), Decimal("10000"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    payments = scheduled_payments(installments)
    assert len(payments) == 360
    assert payments[:12] == [Decimal("804.62")] * 12
    assert payments[12] < Decimal("1025.31")
    assert len(set(payments[12:359])) == 1
    last = installments[-1]
    assert (last.year, last.month.value) == (2054, 12)
    assert last.balance.after == Decimal("0")
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True


@pytest.mark.parametrize(
    "mode",
    [InterestRateApplication.ProratedByPaymentPeriod, InterestRateApplication.ProratedByDaysInMonth],
)
def test_mid_period_rate_change_blends_interest_then_recalculates_from_next_period(mode):
    schedule = AmortizationSchedule(
        amount=100_000, term=Term(30), interest_rate=Decimal("9"), interest_rate_application=mode
    )
    schedule.add_interest_rate_change(datetime.date(2026, 1, 20), Decimal("12"))
    installments = list(schedule.generate(datetime.date(2025, 1, 10)))

    rows = [inst for inst in installments if inst.i is not None]
    payments = scheduled_payments(installments)
    assert len(payments) == 360
    assert payments[:13] == [Decimal("804.62")] * 13
    assert rows[12].balance.before.quantize(CENT) == Decimal("99314.81")
    assert rows[12].payment.interest.quantize(CENT) == Decimal("930.57")
    assert payments[13] > Decimal("1025.31")
    assert len(set(payments[13:359])) == 1
    assert installments[-1].balance.after == Decimal("0")
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True
