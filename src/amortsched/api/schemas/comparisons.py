import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from amortsched.api.schemas.plans import EarlyPaymentFeesSchema, TermSchema
from amortsched.app.queries.comparisons import PlanComparison, PlanComparisonItem


class PlanComparisonRequest(BaseModel):
    plan_ids: list[uuid.UUID] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def validate_unique_plan_ids(self) -> "PlanComparisonRequest":
        if len(set(self.plan_ids)) != len(self.plan_ids):
            raise ValueError("Plan selection must not contain duplicates")
        return self


class AdjustmentCountsResponse(BaseModel):
    one_time_extra_payments: int
    recurring_extra_payments: int
    interest_rate_changes: int


class PlanComparisonItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    lender: str | None
    principal: Decimal
    interest_rate: Decimal
    term: TermSchema
    start_date: datetime.date
    starting_monthly_payment: Decimal
    configured_early_payment_fees: EarlyPaymentFeesSchema
    upfront_fees: Decimal
    total_principal: Decimal
    total_interest: Decimal
    schedule_fees: Decimal
    schedule_total_outflow: Decimal
    total_cost: Decimal
    payoff_month: str
    paid_off: bool
    adjustment_counts: AdjustmentCountsResponse

    @classmethod
    def from_result(cls, item: PlanComparisonItem) -> "PlanComparisonItemResponse":
        return cls(
            id=item.id,
            name=item.name,
            lender=item.lender,
            principal=item.principal,
            interest_rate=item.interest_rate,
            term=TermSchema(years=item.term.years, months=item.term.months),
            start_date=item.start_date,
            starting_monthly_payment=item.starting_monthly_payment,
            configured_early_payment_fees=EarlyPaymentFeesSchema(
                fixed=Decimal(item.configured_early_payment_fees.fixed),
                percent=Decimal(item.configured_early_payment_fees.percent),
            ),
            upfront_fees=item.upfront_fees,
            total_principal=item.total_principal,
            total_interest=item.total_interest,
            schedule_fees=item.schedule_fees,
            schedule_total_outflow=item.schedule_total_outflow,
            total_cost=item.total_cost.quantize(Decimal("0.01")),
            payoff_month=item.payoff_month,
            paid_off=item.paid_off,
            adjustment_counts=AdjustmentCountsResponse(
                one_time_extra_payments=item.adjustment_counts.one_time_extra_payments,
                recurring_extra_payments=item.adjustment_counts.recurring_extra_payments,
                interest_rate_changes=item.adjustment_counts.interest_rate_changes,
            ),
        )


class PlanComparisonResponse(BaseModel):
    directly_comparable: bool
    incomparability_reasons: list[str]
    overall_winner_plan_ids: list[uuid.UUID]
    savings_vs_next_best: Decimal | None
    best_plan_ids_by_metric: dict[str, list[uuid.UUID]]
    plans: list[PlanComparisonItemResponse]

    @classmethod
    def from_result(cls, result: PlanComparison) -> "PlanComparisonResponse":
        return cls(
            directly_comparable=result.directly_comparable,
            incomparability_reasons=list(result.incomparability_reasons),
            overall_winner_plan_ids=list(result.overall_winner_plan_ids),
            savings_vs_next_best=result.savings_vs_next_best,
            best_plan_ids_by_metric={key: list(ids) for key, ids in result.best_plan_ids_by_metric.items()},
            plans=[PlanComparisonItemResponse.from_result(item) for item in result.plans],
        )
