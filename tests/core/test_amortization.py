import datetime
from decimal import Decimal

from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.values import Term


def test_basic_amortization():
    schedule = AmortizationSchedule(amount=100_000, term=Term(30), interest_rate=Decimal("5.0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) > 0
    assert schedule.last_totals is not None
    assert schedule.last_totals.months == 360
    # Principal paid should be close to the original amount (within rounding tolerance)
    assert abs(schedule.last_totals.principal - Decimal("100000")) < Decimal("200")


def test_zero_interest_rate():
    schedule = AmortizationSchedule(amount=12_000, term=Term(1), interest_rate=Decimal("0"))
    installments = list(schedule.generate(datetime.date(2025, 1, 1)))
    assert len(installments) == 12
    assert all(inst.payment.interest == Decimal("0") for inst in installments)
