from decimal import Decimal

import pytest

from amortsched.core.calculators import (
    AffordabilityInput,
    LimitingRatio,
    PrepayVsInvestInput,
    RefinanceInput,
    Strategy,
    affordability,
    amortize,
    level_payment,
    prepay_vs_invest,
    refinance,
)
from amortsched.core.errors import ValidationError

D = Decimal


def close(a: Decimal, b: Decimal, tolerance: str = "0.01") -> bool:
    return abs(a - b) <= D(tolerance)


def test_level_payment_matches_standard_formula():
    assert close(level_payment(D(200000), D("6.5"), 360), D("1264.14"))
    assert level_payment(D(1200), D(0), 12) == D(100)


def test_amortize_pays_off_exactly_and_extra_shortens_term():
    plain = amortize(D(100000), D(5), 120)
    assert len(plain) == 120
    assert plain[-1].balance == 0

    faster = amortize(D(100000), D(5), 120, extra_monthly=D(500))
    assert faster[-1].balance == 0
    assert len(faster) < 120
    assert sum(row.interest for row in faster) < sum(row.interest for row in plain)


def base_affordability(**overrides) -> AffordabilityInput:
    values = {
        "gross_monthly_income": D(10000),
        "monthly_debts": D(0),
        "down_payment": D(100000),
        "interest_rate": D(6),
        "term_months": 360,
    }
    return AffordabilityInput(**{**values, **overrides})


def test_affordability_uses_front_end_ratio_when_debts_are_low():
    result = affordability(base_affordability())
    assert result.limiting_ratio is LimitingRatio.FrontEnd
    assert result.max_monthly_housing == D(2800)
    assert close(result.monthly.total, D(2800), "6")
    assert result.monthly.total <= D(2800)
    assert result.max_home_price == result.max_loan_amount + D(100000)


def test_affordability_uses_back_end_ratio_when_debts_are_high():
    result = affordability(base_affordability(monthly_debts=D(1500)))
    assert result.limiting_ratio is LimitingRatio.BackEnd
    assert result.max_monthly_housing == D(2100)
    assert result.back_end_ratio <= D(36)


def test_affordability_includes_tax_and_pmi_when_ltv_is_high():
    result = affordability(
        base_affordability(down_payment=D(20000), property_tax_rate=D("1.2"), pmi_annual_rate=D("0.5"))
    )
    assert result.monthly.pmi > 0
    assert result.ltv is not None and result.ltv > 80
    assert result.monthly.property_tax == (result.max_home_price * D("1.2") / 100 / 12)
    assert result.monthly.total <= D(2800)


def test_affordability_caps_price_at_80_percent_ltv_when_pmi_would_not_fit():
    result = affordability(base_affordability(down_payment=D(90000), pmi_annual_rate=D(12)))
    assert result.monthly.pmi == 0
    assert result.max_home_price == D(450000)
    assert result.ltv == D(80)


def test_affordability_with_no_budget_left():
    result = affordability(base_affordability(monthly_debts=D(4000), down_payment=D(0)))
    assert result.max_home_price == 0
    assert result.max_monthly_housing == 0
    assert result.ltv is None


def test_affordability_validates_inputs():
    with pytest.raises(ValidationError) as error:
        affordability(base_affordability(gross_monthly_income=D(0), term_months=0))
    assert {item["field"] for item in error.value.errors} == {"gross_monthly_income", "interest_months"}


def test_refinance_break_even_accounts_for_cash_closing_costs():
    result = refinance(
        RefinanceInput(
            current_balance=D(300000),
            current_rate=D(7),
            remaining_months=300,
            new_rate=D("5.5"),
            new_term_months=300,
            closing_costs=D(6000),
        )
    )
    assert result.monthly_savings > 0
    assert result.cash_due_at_closing == D(6000)
    assert result.break_even_month is not None
    naive = int(D(6000) / result.monthly_savings) + 1
    assert result.break_even_month <= naive
    assert result.advantage_by_month[0] == D("-6000.00")
    assert result.advantage_by_month[result.break_even_month] >= 0
    assert result.advantage_by_month[result.break_even_month - 1] < 0
    assert result.lifetime_savings == result.current_total_paid - result.new_total_paid


def test_refinance_rolling_costs_increases_principal_and_needs_no_cash():
    result = refinance(
        RefinanceInput(
            current_balance=D(200000),
            current_rate=D(6),
            remaining_months=240,
            new_rate=D(5),
            new_term_months=240,
            closing_costs=D(4000),
            roll_costs_into_loan=True,
        )
    )
    assert result.new_principal == D(204000)
    assert result.cash_due_at_closing == 0
    assert result.advantage_by_month[0] == D("-4000.00")


def test_refinance_to_a_higher_rate_never_breaks_even():
    result = refinance(
        RefinanceInput(
            current_balance=D(100000),
            current_rate=D(4),
            remaining_months=120,
            new_rate=D(6),
            new_term_months=120,
            closing_costs=D(1000),
        )
    )
    assert result.break_even_month is None
    assert result.monthly_savings < 0
    assert result.lifetime_savings < 0


def prepay_input(annual_return: str) -> PrepayVsInvestInput:
    return PrepayVsInvestInput(
        principal=D(200000),
        interest_rate=D(6),
        term_months=360,
        extra_monthly=D(300),
        annual_return=D(annual_return),
    )


def test_prepaying_wins_when_returns_are_below_the_loan_rate():
    result = prepay_vs_invest(prepay_input("3"))
    assert result.better_strategy is Strategy.Prepay
    assert result.months_saved > 0
    assert result.interest_saved > 0
    assert result.prepay_net_worth > result.invest_net_worth
    assert len(result.timeline) == 360


def test_investing_wins_when_returns_exceed_the_loan_rate():
    result = prepay_vs_invest(prepay_input("9"))
    assert result.better_strategy is Strategy.Invest
    assert result.advantage == result.invest_net_worth - result.prepay_net_worth


def test_break_even_return_equals_the_loan_rate():
    result = prepay_vs_invest(prepay_input("7"))
    assert result.break_even_return == D("6.00")
