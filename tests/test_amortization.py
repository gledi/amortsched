import datetime
from decimal import Decimal

from amortsched.amortization import AmortizationSchedule, EarlyPaymentFees, PaymentKind


def test_one_time_extra_payment_reduces_balance_and_has_no_installment_number() -> None:
    schedule = AmortizationSchedule(
        amount=Decimal("1000"),
        term=(1, 0),
        interest_rate=Decimal("0"),
        early_payment_fees=EarlyPaymentFees(fixed=Decimal("10"), percent=Decimal("1")),
    )

    start = datetime.date(2025, 1, 1)
    schedule.add_one_time_extra_payment(datetime.date(2025, 1, 15), Decimal("200"))

    rows = list(schedule.generate(start_date=start))

    assert rows[0].payment.kind == PaymentKind.ScheduledPayment
    assert rows[0].i == 1

    extra_rows = [r for r in rows if r.payment.kind == PaymentKind.OneTimeExtraPayment]
    assert len(extra_rows) == 1
    assert extra_rows[0].i is None

    # Balance decreased by the *principal portion* of the extra payment.
    assert extra_rows[0].balance.after == extra_rows[0].balance.before - extra_rows[0].payment.principal

    # Fees are computed from the *payment amount* (not remaining principal) in current implementation.
    requested_amount = Decimal("200")
    expected_fee = Decimal("10") + (Decimal("1") / Decimal("100")) * requested_amount
    assert extra_rows[0].payment.fees == expected_fee
    assert extra_rows[0].payment.principal == requested_amount - expected_fee


def test_recurring_extra_payments_apply_count_times() -> None:
    schedule = AmortizationSchedule(
        amount=Decimal("1000"),
        term=(1, 0),
        interest_rate=Decimal("0"),
        early_payment_fees=EarlyPaymentFees(fixed=Decimal("0"), percent=Decimal("0")),
    )

    start = datetime.date(2025, 1, 1)
    schedule.add_recurring_extra_payment(start_date=datetime.date(2025, 2, 1), amount=Decimal("50"), count=3)

    rows = list(schedule.generate(start_date=start))
    recurring_rows = [r for r in rows if r.payment.kind == PaymentKind.RecurringExtraPayment]

    assert len(recurring_rows) == 3
    # Extra payments should not have installment number
    assert all(r.i is None for r in recurring_rows)
