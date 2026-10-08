import datetime
import uuid
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, model_validator

from amortsched.core.calculators import (
    AffordabilityInput,
    AffordabilityResult,
    LimitingRatio,
    PrepayVsInvestResult,
    RefinanceResult,
    Strategy,
)
from amortsched.core.money import round_cents


def money(value: Decimal) -> Decimal:
    return round_cents(value)


class AffordabilityRequest(BaseModel):
    gross_monthly_income: Decimal = Field(gt=0)
    monthly_debts: Decimal = Field(default=Decimal("0"), ge=0)
    down_payment: Decimal = Field(default=Decimal("0"), ge=0)
    interest_rate: Decimal = Field(ge=0, le=100)
    term_months: int = Field(default=360, ge=1, le=600)
    property_tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    insurance_annual: Decimal = Field(default=Decimal("0"), ge=0)
    hoa_monthly: Decimal = Field(default=Decimal("0"), ge=0)
    pmi_annual_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    front_end_ratio: Decimal = Field(default=Decimal("28"), gt=0, le=100)
    back_end_ratio: Decimal = Field(default=Decimal("36"), gt=0, le=100)

    def to_input(self) -> AffordabilityInput:
        return AffordabilityInput(**self.model_dump())


class MonthlyHousingBreakdownResponse(BaseModel):
    principal_interest: Decimal
    property_tax: Decimal
    insurance: Decimal
    hoa: Decimal
    pmi: Decimal
    total: Decimal


class AffordabilityResponse(BaseModel):
    max_home_price: Decimal
    max_loan_amount: Decimal
    max_monthly_housing: Decimal
    limiting_ratio: LimitingRatio
    monthly: MonthlyHousingBreakdownResponse
    front_end_ratio: Decimal
    back_end_ratio: Decimal
    ltv: Decimal | None
    down_payment_percent: Decimal | None

    @classmethod
    def from_result(cls, result: AffordabilityResult) -> "AffordabilityResponse":
        monthly = result.monthly
        return cls(
            max_home_price=result.max_home_price,
            max_loan_amount=money(result.max_loan_amount),
            max_monthly_housing=money(result.max_monthly_housing),
            limiting_ratio=result.limiting_ratio,
            monthly=MonthlyHousingBreakdownResponse(
                principal_interest=money(monthly.principal_interest),
                property_tax=money(monthly.property_tax),
                insurance=money(monthly.insurance),
                hoa=money(monthly.hoa),
                pmi=money(monthly.pmi),
                total=money(monthly.total),
            ),
            front_end_ratio=money(result.front_end_ratio),
            back_end_ratio=money(result.back_end_ratio),
            ltv=None if result.ltv is None else money(result.ltv),
            down_payment_percent=None if result.down_payment_percent is None else money(result.down_payment_percent),
        )


class RefinanceRequest(BaseModel):
    plan_id: uuid.UUID | None = None
    as_of: datetime.date | None = None
    current_balance: Decimal | None = Field(default=None, gt=0)
    current_rate: Decimal | None = Field(default=None, ge=0, le=100)
    remaining_months: int | None = Field(default=None, ge=1, le=600)
    new_rate: Decimal = Field(ge=0, le=100)
    new_term_months: int = Field(ge=1, le=600)
    closing_costs: Decimal = Field(default=Decimal("0"), ge=0)
    roll_costs_into_loan: bool = False

    @model_validator(mode="after")
    def require_loan_source(self) -> Self:
        manual = (self.current_balance, self.current_rate, self.remaining_months)
        if self.plan_id is None and any(value is None for value in manual):
            raise ValueError("Provide plan_id or current_balance, current_rate and remaining_months")
        return self


class CurrentLoanResponse(BaseModel):
    balance: Decimal
    rate: Decimal
    remaining_months: int
    currency: str | None


class RefinanceResponse(BaseModel):
    current_loan: CurrentLoanResponse
    current_payment: Decimal
    new_payment: Decimal
    monthly_savings: Decimal
    new_principal: Decimal
    cash_due_at_closing: Decimal
    current_total_interest: Decimal
    new_total_interest: Decimal
    current_total_paid: Decimal
    new_total_paid: Decimal
    lifetime_savings: Decimal
    break_even_month: int | None
    advantage_by_month: list[Decimal]

    @classmethod
    def from_result(cls, current_loan: CurrentLoanResponse, result: RefinanceResult) -> "RefinanceResponse":
        return cls(
            current_loan=current_loan,
            current_payment=money(result.current_payment),
            new_payment=money(result.new_payment),
            monthly_savings=money(result.monthly_savings),
            new_principal=money(result.new_principal),
            cash_due_at_closing=money(result.cash_due_at_closing),
            current_total_interest=money(result.current_total_interest),
            new_total_interest=money(result.new_total_interest),
            current_total_paid=money(result.current_total_paid),
            new_total_paid=money(result.new_total_paid),
            lifetime_savings=money(result.lifetime_savings),
            break_even_month=result.break_even_month,
            advantage_by_month=list(result.advantage_by_month),
        )


class PrepayVsInvestRequest(BaseModel):
    plan_id: uuid.UUID | None = None
    principal: Decimal | None = Field(default=None, gt=0)
    interest_rate: Decimal | None = Field(default=None, ge=0, le=100)
    term_months: int | None = Field(default=None, ge=1, le=600)
    extra_monthly: Decimal = Field(gt=0)
    annual_return: Decimal = Field(ge=-50, le=50)

    @model_validator(mode="after")
    def require_loan_source(self) -> Self:
        manual = (self.principal, self.interest_rate, self.term_months)
        if self.plan_id is None and any(value is None for value in manual):
            raise ValueError("Provide plan_id or principal, interest_rate and term_months")
        return self


class LoanTermsResponse(BaseModel):
    principal: Decimal
    interest_rate: Decimal
    term_months: int
    currency: str | None


class NetWorthPointResponse(BaseModel):
    month: int
    prepay: Decimal
    invest: Decimal


class PrepayVsInvestResponse(BaseModel):
    loan: LoanTermsResponse
    regular_payment: Decimal
    payoff_months_with_prepayment: int
    months_saved: int
    interest_without_prepayment: Decimal
    interest_with_prepayment: Decimal
    interest_saved: Decimal
    prepay_net_worth: Decimal
    invest_net_worth: Decimal
    advantage: Decimal
    better_strategy: Strategy
    break_even_return: Decimal | None
    timeline: list[NetWorthPointResponse]

    @classmethod
    def from_result(cls, loan: LoanTermsResponse, result: PrepayVsInvestResult) -> "PrepayVsInvestResponse":
        return cls(
            loan=loan,
            regular_payment=money(result.regular_payment),
            payoff_months_with_prepayment=result.payoff_months_with_prepayment,
            months_saved=result.months_saved,
            interest_without_prepayment=money(result.interest_without_prepayment),
            interest_with_prepayment=money(result.interest_with_prepayment),
            interest_saved=money(result.interest_saved),
            prepay_net_worth=money(result.prepay_net_worth),
            invest_net_worth=money(result.invest_net_worth),
            advantage=money(result.advantage),
            better_strategy=result.better_strategy,
            break_even_return=result.break_even_return,
            timeline=[
                NetWorthPointResponse(month=point.month, prepay=money(point.prepay), invest=money(point.invest))
                for point in result.timeline
            ],
        )
