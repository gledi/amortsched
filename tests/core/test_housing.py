import datetime
import uuid
from decimal import Decimal

import pytest

from amortsched.core.entities import Plan
from amortsched.core.errors import ValidationError
from amortsched.core.values import HousingCosts, Term


def make_plan(amount: str, housing: HousingCosts, years: int = 30, rate: str = "6") -> Plan:
    return Plan(
        user_id=uuid.uuid4(),
        name="Home",
        slug="home",
        amount=Decimal(amount),
        term=Term(years),
        interest_rate=Decimal(rate),
        start_date=datetime.date(2026, 1, 1),
        housing_costs=housing,
    )


def test_escrow_is_attached_to_every_scheduled_installment():
    costs = HousingCosts(
        property_tax_annual=Decimal("2400"),
        insurance_annual=Decimal("1200"),
        hoa_monthly=Decimal("50"),
    )
    schedule = make_plan("12000", costs, years=1, rate="0").generate()

    scheduled = [item for item in schedule.installments if item.i is not None]
    assert len(scheduled) == 12
    assert all(item.housing is not None and item.housing.total == Decimal("350") for item in scheduled)
    assert schedule.totals is not None
    assert schedule.totals.escrow == Decimal("4200")
    assert schedule.totals.pmi == Decimal("0")


def test_pmi_stops_once_balance_falls_to_cancellation_ltv():
    costs = HousingCosts(property_value=Decimal("1000"), pmi_annual_rate=Decimal("12"), pmi_cancel_ltv=Decimal("78"))
    schedule = make_plan("900", costs, years=1, rate="0").generate()

    pmi = [item.housing.pmi for item in schedule.installments if item.housing is not None]
    assert pmi[:2] == [Decimal("9"), Decimal("9")]
    assert all(value == Decimal("0") for value in pmi[2:])
    assert schedule.totals is not None
    assert schedule.totals.pmi == Decimal("18")


def test_down_payment_ltv_and_starting_housing_payment():
    costs = HousingCosts(
        property_value=Decimal("400000"), property_tax_annual=Decimal("4800"), pmi_annual_rate=Decimal("0.6")
    )
    plan = make_plan("360000", costs)

    assert costs.down_payment(plan.amount) == Decimal("40000")
    assert costs.ltv_percent(plan.amount) == Decimal("90")
    housing = plan.starting_housing_payment
    assert housing is not None
    assert housing.property_tax == Decimal("400")
    assert housing.pmi == Decimal("180")


def test_plans_without_housing_costs_have_no_housing_rows():
    schedule = make_plan("1200", HousingCosts(), years=1, rate="0").generate()
    assert all(item.housing is None for item in schedule.installments)
    assert make_plan("1200", HousingCosts()).starting_housing_payment is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pmi_annual_rate": Decimal("0.5")},
        {"property_value": Decimal("0")},
        {"property_tax_annual": Decimal("-1")},
        {"property_value": Decimal("1"), "pmi_cancel_ltv": Decimal("0")},
    ],
)
def test_invalid_housing_costs_raise_validation_errors(kwargs):
    with pytest.raises(ValidationError):
        HousingCosts(**kwargs)
