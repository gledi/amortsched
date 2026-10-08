"""Level-payment formula shared by plan schedules and decision calculators."""

from decimal import Decimal

from amortsched.core.money import HUNDRED, round_cents

TWELVE = Decimal("12")


def monthly_rate(annual_rate_percent: Decimal) -> Decimal:
    return annual_rate_percent / HUNDRED / TWELVE


def payment_factor(annual_rate_percent: Decimal, months: int) -> Decimal:
    """Level monthly payment per unit of principal."""
    rate = monthly_rate(annual_rate_percent)
    if rate == 0:
        return Decimal(1) / Decimal(months)
    growth = (1 + rate) ** months
    return rate * growth / (growth - 1)


def level_payment(principal: Decimal, annual_rate_percent: Decimal, months: int) -> Decimal:
    return principal * payment_factor(annual_rate_percent, months)


def monthly_payment(principal: Decimal, annual_rate_percent: Decimal, months: int) -> Decimal:
    return round_cents(level_payment(principal, annual_rate_percent, months))
