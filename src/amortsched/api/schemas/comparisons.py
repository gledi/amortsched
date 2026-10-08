import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from amortsched.api.schemas.plans import EarlyPaymentFeesSchema, TermSchema
from amortsched.app.queries.comparisons import HorizonCost, PlanComparison, PlanComparisonItem
from amortsched.core.money import round_cents
from amortsched.core.values import LoanType


class PlanComparisonRequest(BaseModel):
    plan_ids: list[uuid.UUID] = Field(min_length=2, max_length=4)
    horizon_months: int | None = Field(default=None, ge=1, le=600)

    @model_validator(mode="after")
    def validate_unique_plan_ids(self) -> "PlanComparisonRequest":
        if len(set(self.plan_ids)) != len(self.plan_ids):
            raise ValueError("Plan selection must not contain duplicates")
        return self


class AdjustmentCountsResponse(BaseModel):
    one_time_extra_payments: int
    recurring_extra_payments: int
    interest_rate_changes: int


class HorizonCostResponse(BaseModel):
    months: int
    cost: Decimal
    balance: Decimal
    payoff_penalty: Decimal

    @classmethod
    def from_result(cls, horizon: HorizonCost) -> "HorizonCostResponse":
        return cls(
            months=horizon.months,
            cost=horizon.cost,
            balance=horizon.balance,
            payoff_penalty=horizon.payoff_penalty,
        )


class PlanComparisonItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    lender: str | None
    currency: str
    loan_type: LoanType
    principal: Decimal
    interest_rate: Decimal
    term: TermSchema
    start_date: datetime.date
    starting_monthly_payment: Decimal
    starting_monthly_housing: Decimal
    starting_total_monthly_payment: Decimal
    down_payment: Decimal | None
    ltv: Decimal | None
    configured_early_payment_fees: EarlyPaymentFeesSchema
    upfront_fees: Decimal
    total_principal: Decimal
    total_interest: Decimal
    schedule_fees: Decimal
    schedule_total_outflow: Decimal
    total_pmi: Decimal
    total_escrow: Decimal
    total_cost: Decimal
    payoff_months: int
    payoff_month: str
    paid_off: bool
    adjustment_counts: AdjustmentCountsResponse
    cumulative_cost: list[Decimal]
    horizon: HorizonCostResponse | None

    @classmethod
    def from_result(cls, item: PlanComparisonItem) -> "PlanComparisonItemResponse":
        return cls(
            id=item.id,
            name=item.name,
            lender=item.lender,
            currency=item.currency,
            loan_type=item.loan_type,
            principal=item.principal,
            interest_rate=item.interest_rate,
            term=TermSchema(years=item.term.years, months=item.term.months),
            start_date=item.start_date,
            starting_monthly_payment=round_cents(item.starting_monthly_payment),
            starting_monthly_housing=round_cents(item.starting_monthly_housing),
            starting_total_monthly_payment=round_cents(item.starting_total_monthly_payment),
            down_payment=item.down_payment,
            ltv=item.ltv,
            configured_early_payment_fees=EarlyPaymentFeesSchema(
                fixed=Decimal(item.configured_early_payment_fees.fixed),
                percent=Decimal(item.configured_early_payment_fees.percent),
            ),
            upfront_fees=item.upfront_fees,
            total_principal=item.total_principal,
            total_interest=item.total_interest,
            schedule_fees=item.schedule_fees,
            schedule_total_outflow=item.schedule_total_outflow,
            total_pmi=round_cents(item.total_pmi),
            total_escrow=round_cents(item.total_escrow),
            total_cost=round_cents(item.total_cost),
            payoff_months=item.payoff_months,
            payoff_month=item.payoff_month,
            paid_off=item.paid_off,
            adjustment_counts=AdjustmentCountsResponse(
                one_time_extra_payments=item.adjustment_counts.one_time_extra_payments,
                recurring_extra_payments=item.adjustment_counts.recurring_extra_payments,
                interest_rate_changes=item.adjustment_counts.interest_rate_changes,
            ),
            cumulative_cost=list(item.cumulative_cost),
            horizon=None if item.horizon is None else HorizonCostResponse.from_result(item.horizon),
        )


class PlanComparisonResponse(BaseModel):
    directly_comparable: bool
    incomparability_reasons: list[str]
    overall_winner_plan_ids: list[uuid.UUID]
    savings_vs_next_best: Decimal | None
    best_plan_ids_by_metric: dict[str, list[uuid.UUID]]
    plans: list[PlanComparisonItemResponse]
    horizon_months: int | None
    horizon_winner_plan_ids: list[uuid.UUID]

    @classmethod
    def from_result(cls, result: PlanComparison) -> "PlanComparisonResponse":
        return cls(
            directly_comparable=result.directly_comparable,
            incomparability_reasons=list(result.incomparability_reasons),
            overall_winner_plan_ids=list(result.overall_winner_plan_ids),
            savings_vs_next_best=result.savings_vs_next_best,
            best_plan_ids_by_metric={key: list(ids) for key, ids in result.best_plan_ids_by_metric.items()},
            plans=[PlanComparisonItemResponse.from_result(item) for item in result.plans],
            horizon_months=result.horizon_months,
            horizon_winner_plan_ids=list(result.horizon_winner_plan_ids),
        )
