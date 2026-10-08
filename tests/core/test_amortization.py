import datetime
from decimal import Decimal

import pytest

from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.calculators import amortize
from amortsched.core.errors import InvalidTermError
from amortsched.core.values import EarlyPaymentFees, InterestRateApplication, Term


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


def scheduled_payments(installments):
    return [inst.payment.total for inst in installments if inst.i is not None]


def test_rate_change_recalculates_payment_reg_z_example_a():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("9"))
    schedule.add_interest_rate_change(datetime.date(2026, 1, 1), Decimal("12"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    payments = scheduled_payments(installments)
    assert len(payments) == 360
    assert payments[:12] == [Decimal("804.62")] * 12
    assert payments[12:359] == [Decimal("1025.31")] * 347
    assert payments[359] < Decimal("1025.31") * 2
    assert payments[0] * 12 + payments[12] * 348 - 100_000 == Decimal("266463.32")
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
    assert payments[0] * 12 + payments[12] * 12 + payments[24] * 336 - 100_000 == Decimal("265234.76")
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
    assert zero_rate_rows[0].balance.before == Decimal("6179.48")
    assert [inst.payment.total for inst in zero_rate_rows[:11]] == [Decimal("514.96")] * 11
    assert zero_rate_rows[-1].payment.total == Decimal("514.92")
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
    assert schedule.starting_payment(datetime.date(2025, 1, 1)) == Decimal("804.62")
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
    assert rows[12].balance.before == Decimal("99314.84")
    assert rows[12].payment.interest == Decimal("930.57")
    assert payments[13] > Decimal("1025.31")
    assert len(set(payments[13:359])) == 1
    assert installments[-1].balance.after == Decimal("0")
    assert schedule.last_totals is not None
    assert schedule.last_totals.paid_off is True


def test_fixed_rate_schedule_in_whole_cents_cfpb_h24b():
    schedule = AmortizationSchedule(amount=162_000, term=Term(30), interest_rate=Decimal("3.875"))
    installments = list(schedule.generate(datetime.date(2013, 5, 1)))

    rows = [inst for inst in installments if inst.i is not None]
    assert len(rows) == 360
    assert schedule.starting_payment(datetime.date(2013, 5, 1)) == Decimal("761.78")
    assert [row.payment.total for row in rows[:359]] == [Decimal("761.78")] * 359
    assert rows[0].payment.interest == Decimal("523.13")
    assert rows[0].payment.principal == Decimal("238.65")
    assert rows[0].balance.after == Decimal("161761.35")
    assert rows[-1].payment.total == Decimal("764.68")
    assert rows[-1].payment.interest == Decimal("2.46")
    assert rows[-1].balance.after == Decimal("0")


def test_mid_period_extra_payment_rounds_period_interest_once():
    schedule = AmortizationSchedule(amount=10_003, term=Term(1), interest_rate=Decimal("6"))
    schedule.add_one_time_extra_payment(datetime.date(2025, 1, 16), Decimal("1000"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    first = next(inst for inst in installments if inst.i == 1)
    assert first.payment.interest == Decimal("50.02")


def test_early_payment_penalty_is_rounded_half_up_to_the_cent():
    schedule = AmortizationSchedule(
        amount=10_000,
        term=Term(1),
        interest_rate=Decimal("6"),
        early_payment_fees=EarlyPaymentFees(percent=Decimal("1")),
    )
    schedule.add_one_time_extra_payment(datetime.date(2025, 3, 15), Decimal("1000.50"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))

    extra = next(inst for inst in installments if inst.i is None)
    assert extra.payment.fees == Decimal("10.01")
    assert extra.payment.principal == Decimal("990.49")


def whole_cents(value):
    return value == value.quantize(Decimal("0.01"))


@pytest.mark.parametrize("mode", list(InterestRateApplication))
def test_every_row_is_whole_cents_and_rows_sum_to_totals(mode):
    schedule = AmortizationSchedule(
        amount=Decimal("250000"),
        term=Term(30),
        interest_rate=Decimal("6.125"),
        early_payment_fees=EarlyPaymentFees(fixed=Decimal("25"), percent=Decimal("1.5")),
        interest_rate_application=mode,
    )
    schedule.add_interest_rate_change(datetime.date(2028, 7, 20), Decimal("7.375"))
    schedule.add_interest_rate_change(datetime.date(2031, 3, 1), Decimal("5.5"))
    schedule.add_one_time_extra_payment(datetime.date(2026, 4, 17), Decimal("12345.67"))
    schedule.add_recurring_extra_payment(datetime.date(2027, 2, 14), Decimal("333.33"), count=24)
    installments = list(schedule.generate(datetime.date(2025, 1, 10)))

    for inst in installments:
        amounts = (
            inst.payment.principal,
            inst.payment.interest,
            inst.payment.fees,
            inst.balance.before,
            inst.balance.after,
        )
        assert all(whole_cents(amount) for amount in amounts), inst
    totals = schedule.last_totals
    assert totals is not None
    assert totals.paid_off is True
    assert installments[-1].balance.after == Decimal("0")
    assert sum(inst.payment.principal for inst in installments) == totals.principal
    assert sum(inst.payment.interest for inst in installments) == totals.interest
    assert sum(inst.payment.fees for inst in installments) == totals.fees


@pytest.mark.parametrize(
    ("amount", "rate", "years"),
    [
        (Decimal("162000"), Decimal("3.875"), 30),
        (Decimal("25000"), Decimal("7.49"), 5),
        (Decimal("9000"), Decimal("0"), 3),
    ],
)
def test_plan_schedule_matches_decision_tool_schedule_to_the_cent(amount, rate, years):
    schedule = AmortizationSchedule(amount=amount, term=Term(years), interest_rate=rate)
    engine_rows = [
        (inst.payment.total, inst.payment.interest, inst.payment.principal, inst.balance.after)
        for inst in schedule.generate(datetime.date(2025, 1, 1))
    ]
    tool_rows = [(row.payment, row.interest, row.principal, row.balance) for row in amortize(amount, rate, years * 12)]

    assert engine_rows == tool_rows


def test_extra_payment_payoff_row_carries_the_period_interest():
    schedule = AmortizationSchedule(amount=Decimal("10000"), term=Term(1), interest_rate=Decimal("6"))
    schedule.add_one_time_extra_payment(datetime.date(2025, 3, 15), Decimal("20000"))

    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    totals = schedule.last_totals

    assert totals is not None and totals.paid_off is True
    payoff = installments[-1]
    assert payoff.i is None
    assert payoff.balance.after == Decimal("0.00")
    assert payoff.payment.interest > 0
    assert sum(inst.payment.interest for inst in installments) == totals.interest
    assert sum(inst.payment.principal for inst in installments) == totals.principal


def test_extra_payments_dated_on_payment_dates_are_each_applied_once():
    schedule = AmortizationSchedule(amount=1000, term=Term(0, 4), interest_rate=Decimal("12"))
    schedule.add_one_time_extra_payment(datetime.date(2026, 12, 1), Decimal("50"))
    schedule.add_recurring_extra_payment(datetime.date(2026, 11, 1), Decimal("100"), count=3)

    rows = list(schedule.generate(datetime.date(2026, 11, 1)))

    periods = [(row.i, int(row.month), row.payment.principal) for row in rows if row.i is None or row.i < 4]
    assert [(i, month) for i, month, _ in periods] == [
        (None, 11),
        (1, 11),
        (None, 12),
        (None, 12),
        (2, 12),
        (None, 1),
        (3, 1),
    ]
    assert sum(principal for i, _, principal in periods if i is None) == Decimal("350")
