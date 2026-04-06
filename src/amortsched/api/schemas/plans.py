import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from amortsched.core.entities import Plan
from amortsched.core.values import InterestRateApplication


class TermSchema(BaseModel):
    years: int = 0
    months: int = 0


class EarlyPaymentFeesSchema(BaseModel):
    fixed: Decimal = Decimal("0.00")
    percent: Decimal = Decimal("0.00")


class ExtraPaymentSchema(BaseModel):
    date: datetime.date
    amount: Decimal


class RecurringExtraPaymentSchema(BaseModel):
    start_date: datetime.date
    amount: Decimal
    count: int


class InterestRateChangeSchema(BaseModel):
    effective_date: datetime.date
    rate: Decimal


class CreatePlanRequest(BaseModel):
    name: str
    amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(gt=0, le=100)
    term: TermSchema
    start_date: datetime.date | None = None
    early_payment_fees: EarlyPaymentFeesSchema = Field(default_factory=EarlyPaymentFeesSchema)
    interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth


class UpdatePlanRequest(BaseModel):
    name: str | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    interest_rate: Decimal | None = Field(default=None, gt=0, le=100)
    term: TermSchema | None = None
    start_date: datetime.date | None = None
    early_payment_fees: EarlyPaymentFeesSchema | None = None
    interest_rate_application: InterestRateApplication | None = None


class AddExtraPaymentRequest(BaseModel):
    date: datetime.date
    amount: Decimal = Field(gt=0)


class AddRecurringExtraPaymentRequest(BaseModel):
    start_date: datetime.date
    amount: Decimal = Field(gt=0)
    count: int = Field(gt=0)


class AddInterestRateChangeRequest(BaseModel):
    effective_date: datetime.date
    rate: Decimal = Field(ge=0, le=100)


class PlanResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    slug: str
    amount: Decimal
    interest_rate: Decimal
    term: TermSchema
    start_date: datetime.date
    early_payment_fees: EarlyPaymentFeesSchema
    interest_rate_application: str
    status: str
    one_time_extra_payments: list[ExtraPaymentSchema]
    recurring_extra_payments: list[RecurringExtraPaymentSchema]
    interest_rate_changes: list[InterestRateChangeSchema]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_entity(cls, plan: Plan) -> "PlanResponse":
        return cls(
            id=plan.id,
            user_id=plan.user_id,
            name=plan.name,
            slug=plan.slug,
            amount=plan.amount,
            interest_rate=plan.interest_rate,
            term=TermSchema(years=plan.term.years, months=plan.term.months),
            start_date=plan.start_date,
            early_payment_fees=EarlyPaymentFeesSchema(
                fixed=Decimal(plan.early_payment_fees.fixed),
                percent=Decimal(plan.early_payment_fees.percent),
            ),
            interest_rate_application=plan.interest_rate_application.value,
            status=plan.status.value,
            one_time_extra_payments=[
                ExtraPaymentSchema(date=p.date, amount=p.amount) for p in plan.one_time_extra_payments
            ],
            recurring_extra_payments=[
                RecurringExtraPaymentSchema(start_date=p.start_date, amount=p.amount, count=p.count)
                for p in plan.recurring_extra_payments
            ],
            interest_rate_changes=[
                InterestRateChangeSchema(effective_date=c.effective_date, rate=c.yearly_interest_rate)
                for c in plan.interest_rate_changes
            ],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )


class PaginatedPlansResponse(BaseModel):
    items: list[PlanResponse]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool
