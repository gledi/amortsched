from decimal import Decimal

import pytest

from amortsched.core.money import round_cents


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
