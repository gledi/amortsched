from decimal import Decimal

import pytest

from amortsched.core.money import round_cents, round_percent


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.125", "0.13"),
        ("0.135", "0.14"),
        ("2.675", "2.68"),
        ("1.004", "1.00"),
        ("1.006", "1.01"),
        ("5", "5.00"),
    ],
)
def test_round_cents_rounds_half_up(value: str, expected: str) -> None:
    assert str(round_cents(Decimal(value))) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("79.995", "80.00"),
        ("4.125", "4.13"),
        ("12.3449", "12.34"),
    ],
)
def test_round_percent_rounds_half_up_to_basis_points(value: str, expected: str) -> None:
    assert str(round_percent(Decimal(value))) == expected
