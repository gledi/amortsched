# Coding Standards

Rules for review that no automated check can enforce. Import direction and the single rounding owner are checked by `make lint` and `tests/test_architecture.py`; don't restate them here.

## Rounding names say what is rounded

Money goes through `round_cents`, percentages and ratios through `round_percent`, whole-unit amounts through `floor_units` (all in `core/money.py`). A money helper applied to a percentage, or the reverse, is a violation even when the digits happen to match.

## Request validation stays on request schemas

A Pydantic schema used in both a request and a response carries only constraints that every stored value already satisfies. Input-only constraints (`MoneyInput`, ranges added after data exists) go on a request-only schema or subclass, so values persisted before the constraint existed still serialize instead of failing with a 500.
