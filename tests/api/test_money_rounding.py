from decimal import Decimal

from amortsched.api.schemas.schedules import HousingPaymentSchema
from amortsched.core.values import HousingPayment


def test_housing_payment_response_rounds_exact_half_cent_up() -> None:
    housing = HousingPayment(
        property_tax=Decimal("0.125"),
        insurance=Decimal("0.135"),
        hoa=Decimal("2.675"),
        pmi=Decimal("0.005"),
    )

    schema = HousingPaymentSchema.from_value(housing)

    assert (schema.property_tax, schema.insurance, schema.hoa, schema.pmi) == (
        Decimal("0.13"),
        Decimal("0.14"),
        Decimal("2.68"),
        Decimal("0.01"),
    )
