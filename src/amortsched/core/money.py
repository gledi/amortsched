from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
CENT = Decimal("0.01")
BASIS_POINT = Decimal("0.01")


def round_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def round_percent(value: Decimal) -> Decimal:
    """Round a percentage half-up to two decimal places (whole basis points)."""
    return value.quantize(BASIS_POINT, rounding=ROUND_HALF_UP)
