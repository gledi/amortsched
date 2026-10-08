import datetime
from decimal import Decimal

import pytest

from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.calculators import (
    AffordabilityInput,
    LimitingRatio,
    PeriodRow,
    PrepayVsInvestResult,
    RefinanceResult,
    Strategy,
    affordability,
    period_rows,
    prepay_vs_invest_from_periods,
    refinance_from_periods,
)
from amortsched.core.errors import ValidationError
from amortsched.core.payments import level_payment
from amortsched.core.values import EarlyPaymentFees

D = Decimal


def close(a: Decimal, b: Decimal, tolerance: str = "0.01") -> bool:
    return abs(a - b) <= D(tolerance)


def test_level_payment_matches_standard_formula():
    assert close(level_payment(D(200000), D("6.5"), 360), D("1264.14"))
    assert level_payment(D(1200), D(0), 12) == D(100)


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
    assert result.monthly.property_tax == (result.max_home_price * D("1.2") / 100 / 12).quantize(D("0.01"))
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


def test_affordability_monthly_lines_are_whole_cents_and_total_is_their_sum():
    result = affordability(
        base_affordability(
            down_payment=D(20000),
            property_tax_rate=D("1.2"),
            insurance_annual=D(1000),
            hoa_monthly=D(50),
            pmi_annual_rate=D("0.5"),
        )
    )
    monthly = result.monthly
    lines = (monthly.principal_interest, monthly.property_tax, monthly.insurance, monthly.hoa, monthly.pmi)
    for line in lines:
        assert line == line.quantize(D("0.01"))
    assert monthly.insurance == D("83.33")
    assert monthly.total == sum(lines, D(0))


def test_affordability_validates_inputs():
    with pytest.raises(ValidationError) as error:
        affordability(base_affordability(gross_monthly_income=D(0), term_months=0))
    assert {item["field"] for item in error.value.errors} == {"gross_monthly_income", "interest_months"}


def refinance_on_engine(
    balance: Decimal,
    rate: Decimal,
    months: int,
    new_rate: Decimal,
    new_months: int,
    closing_costs: Decimal,
    roll_costs_into_loan: bool = False,
) -> RefinanceResult:
    start = datetime.date(2026, 1, 1)
    new_principal = balance + (closing_costs if roll_costs_into_loan else D(0))
    return refinance_from_periods(
        current=period_rows(AmortizationSchedule(balance, (0, months), rate).generate(start)),
        current_balance=balance,
        new=period_rows(AmortizationSchedule(new_principal, (0, new_months), new_rate).generate(start)),
        new_principal=new_principal,
        cash_due=D(0) if roll_costs_into_loan else closing_costs,
    )


def test_refinance_break_even_accounts_for_cash_closing_costs():
    result = refinance_on_engine(D(300000), D(7), 300, D("5.5"), 300, D(6000))

    assert result.current_payment == D("2120.34")
    assert result.new_payment == D("1842.26")
    assert result.cash_due_at_closing == D(6000)
    assert result.current_total_interest == D("336100.16")
    assert result.new_total_interest == D("252679.70")
    assert result.new_total_paid == D("558679.70")
    assert result.break_even_month == 17
    assert result.advantage_by_month[0] == D("-6000.00")
    assert result.advantage_by_month[16] == D("-3.85")
    assert result.advantage_by_month[17] == D("370.50")
    assert result.advantage_by_month[-1] == D("77420.46")
    assert len(result.advantage_by_month) == 301


def test_refinance_rolling_costs_increases_principal_and_needs_no_cash():
    result = refinance_on_engine(D(200000), D(6), 240, D(5), 240, D(4000), roll_costs_into_loan=True)

    assert result.new_principal == D(204000)
    assert result.cash_due_at_closing == 0
    assert result.new_payment == D("1346.31")
    assert result.break_even_month == 27
    assert result.advantage_by_month[0] == D("-4000.00")
    assert result.advantage_by_month[26] == D("-137.34")
    assert result.advantage_by_month[27] == D("9.39")
    assert result.lifetime_savings == D("20772.94")


def test_refinance_to_a_higher_rate_never_breaks_even():
    result = refinance_on_engine(D(100000), D(4), 120, D(6), 120, D(1000))

    assert result.break_even_month is None
    assert result.monthly_savings == D("-97.76")
    assert result.lifetime_savings == D("-12730.08")
    assert result.advantage_by_month[-1] == D("-12730.08")


def prepay_on_engine(principal: str, rate: str, months: int, extra: str, annual_return: str) -> PrepayVsInvestResult:
    start = datetime.date(2026, 11, 1)
    baseline = AmortizationSchedule(D(principal), (0, months), D(rate))
    prepay = AmortizationSchedule(D(principal), (0, months), D(rate))
    prepay.add_recurring_extra_payment(start, D(extra), months)
    return prepay_vs_invest_from_periods(
        baseline=period_rows(baseline.generate(start)),
        prepay=period_rows(prepay.generate(start)),
        regular_payment=baseline.starting_payment(start),
        extra_monthly=D(extra),
        annual_return=D(annual_return),
    )


def test_prepay_invests_the_baseline_outflow_plus_extra_left_over_each_period():
    result = prepay_on_engine("1000", "12", 4, "100", "0")
    assert result.regular_payment == D("256.28")
    assert result.payoff_months_with_prepayment == 3
    assert result.months_saved == 1
    assert result.interest_without_prepayment == D("25.13")
    assert result.interest_with_prepayment == D("19.58")
    assert [point.prepay for point in result.timeline] == [D("-653.72"), D("-303.98"), D("49.26"), D("405.55")]
    assert result.prepay_net_worth == D("405.55")
    assert [point.invest for point in result.timeline] == [D("-653.72"), D("-304.98"), D("46.25"), D("400")]
    assert result.advantage == result.interest_saved == D("5.55")
    assert result.better_strategy is Strategy.Prepay


def test_prepaying_wins_when_returns_are_below_the_loan_rate():
    result = prepay_on_engine("200000", "6", 360, "300", "3")
    assert result.better_strategy is Strategy.Prepay
    assert result.months_saved > 0
    assert result.interest_saved > 0
    assert result.prepay_net_worth > result.invest_net_worth
    assert len(result.timeline) == 360


def test_investing_wins_when_returns_exceed_the_loan_rate():
    result = prepay_on_engine("200000", "6", 360, "300", "9")
    assert result.better_strategy is Strategy.Invest
    assert result.advantage == result.invest_net_worth - result.prepay_net_worth


def test_prepay_and_invest_tie_on_an_interest_free_loan_with_no_return():
    result = prepay_on_engine("1200", "0", 12, "100", "0")
    freed_payment_banked_monthly = D(200)
    extra_invested_over_term = 12 * D(100)
    assert result.payoff_months_with_prepayment == 6
    assert result.timeline[6].prepay == result.timeline[6].invest == freed_payment_banked_monthly
    assert result.prepay_net_worth == result.invest_net_worth == extra_invested_over_term
    assert result.advantage == 0
    assert result.better_strategy is Strategy.Tie


def test_break_even_return_equals_the_loan_rate_when_savings_and_loan_both_compound_monthly():
    result = prepay_on_engine("10000", "12", 12, "500", "5")
    assert result.break_even_return == D("12.00")


def test_level_payment_stays_unrounded():
    assert level_payment(D(200000), D("7.5"), 180) == pytest.approx(D("1854.0247200054619"), abs=D("1e-9"))


def engine_rows(schedule: AmortizationSchedule) -> list[PeriodRow]:
    return period_rows(schedule.generate(datetime.date(2026, 1, 1)))


def test_engine_payment_matches_published_pmt_example():
    schedule = AmortizationSchedule(D(10000), (0, 10), D(8))
    assert schedule.starting_payment(datetime.date(2026, 1, 1)) == D("1037.03")


def test_refinance_and_prepay_money_is_whole_cents():
    refi = refinance_from_periods(
        current=engine_rows(AmortizationSchedule(D(300000), (0, 300), D("7.125"))),
        current_balance=D(300000),
        new=engine_rows(AmortizationSchedule(D(300000), (0, 300), D("5.5"))),
        new_principal=D(300000),
        cash_due=D(0),
    )
    for amount in (refi.current_payment, refi.new_payment, refi.current_total_interest, refi.new_total_paid):
        assert amount == amount.quantize(D("0.01"))
    assert prepay_on_engine("200000", "6", 360, "300", "3").regular_payment == D("1199.10")


def test_refinance_from_engine_merges_extra_rows_counts_an_extra_only_final_period_and_reports_the_scheduled_payment():
    current = AmortizationSchedule(D(1200), (1, 0), D(0))
    current.add_one_time_extra_payment(datetime.date(2026, 1, 15), D(50))
    current.add_one_time_extra_payment(datetime.date(2026, 6, 10), D(2000))
    new = AmortizationSchedule(D(1200), (0, 3), D(0))

    result = refinance_from_periods(
        current=engine_rows(current),
        current_balance=D(1200),
        new=engine_rows(new),
        new_principal=D(1200),
        cash_due=D(0),
    )

    assert result.current_payment == D(100)
    assert result.new_payment == D(400)
    assert result.current_total_paid == D(1200)
    assert result.current_total_interest == 0
    assert len(result.advantage_by_month) == 7
    assert result.advantage_by_month[1] == D(0)


def test_prepay_vs_invest_from_engine_counts_extra_payment_fees_as_outflow():
    baseline = AmortizationSchedule(D(1200), (1, 0), D(0))
    prepay = AmortizationSchedule(D(1200), (1, 0), D(0), EarlyPaymentFees(fixed=D(5)))
    prepay.add_recurring_extra_payment(datetime.date(2026, 1, 15), D(100), 12)

    result = prepay_vs_invest_from_periods(
        baseline=engine_rows(baseline),
        prepay=engine_rows(prepay),
        regular_payment=D(100),
        extra_monthly=D(100),
        annual_return=D(0),
    )

    assert result.payoff_months_with_prepayment == 7
    assert result.months_saved == 5
    assert result.interest_saved == 0
    assert len(result.timeline) == 12
    assert result.timeline[0].prepay == D(-1005)
    assert result.timeline[-1].prepay == D(1165)
    assert result.timeline[-1].invest == D(1200)
