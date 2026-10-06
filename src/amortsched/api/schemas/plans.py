import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from amortsched.api.schemas.schedules import HousingPaymentSchema
from amortsched.core.entities import Plan
from amortsched.core.values import (
    HousingCosts,
    InterestRateApplication,
    InterestRateChange,
    LoanType,
    OneTimeExtraPayment,
    RecurringExtraPayment,
)

CENT = Decimal("0.01")


class TermSchema(BaseModel):
    years: int = Field(default=0, ge=0, le=50)
    months: int = Field(default=0, ge=0, le=11)

    @model_validator(mode="after")
    def validate_nonzero(self) -> "TermSchema":
        if self.years == 0 and self.months == 0:
            raise ValueError("Term must be at least one month")
        return self


class EarlyPaymentFeesSchema(BaseModel):
    fixed: Decimal = Field(default=Decimal("0.00"), ge=0)
    percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class HousingCostsSchema(BaseModel):
    property_value: Decimal | None = Field(default=None, gt=0)
    property_tax_annual: Decimal = Field(default=Decimal("0.00"), ge=0)
    insurance_annual: Decimal = Field(default=Decimal("0.00"), ge=0)
    hoa_monthly: Decimal = Field(default=Decimal("0.00"), ge=0)
    pmi_annual_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    pmi_cancel_ltv: Decimal = Field(default=Decimal("78"), gt=0, le=100)

    def to_value(self) -> HousingCosts:
        return HousingCosts(
            property_value=self.property_value,
            property_tax_annual=self.property_tax_annual,
            insurance_annual=self.insurance_annual,
            hoa_monthly=self.hoa_monthly,
            pmi_annual_rate=self.pmi_annual_rate,
            pmi_cancel_ltv=self.pmi_cancel_ltv,
        )

    @classmethod
    def from_value(cls, costs: HousingCosts) -> "HousingCostsSchema":
        return cls(
            property_value=costs.property_value,
            property_tax_annual=costs.property_tax_annual,
            insurance_annual=costs.insurance_annual,
            hoa_monthly=costs.hoa_monthly,
            pmi_annual_rate=costs.pmi_annual_rate,
            pmi_cancel_ltv=costs.pmi_cancel_ltv,
        )


class ExtraPaymentSchema(BaseModel):
    date: datetime.date
    amount: Decimal = Field(gt=0)

    def to_value(self) -> OneTimeExtraPayment:
        return OneTimeExtraPayment(date=self.date, amount=self.amount)


class RecurringExtraPaymentSchema(BaseModel):
    start_date: datetime.date
    amount: Decimal = Field(gt=0)
    count: int = Field(gt=0, le=600)

    def to_value(self) -> RecurringExtraPayment:
        return RecurringExtraPayment(start_date=self.start_date, amount=self.amount, count=self.count)


class InterestRateChangeSchema(BaseModel):
    effective_date: datetime.date
    rate: Decimal = Field(ge=0, le=100)

    def to_value(self) -> InterestRateChange:
        return InterestRateChange(effective_date=self.effective_date, yearly_interest_rate=self.rate)


class AdjustmentsSchema(BaseModel):
    one_time_extra_payments: list[ExtraPaymentSchema] = Field(default_factory=list, max_length=500)
    recurring_extra_payments: list[RecurringExtraPaymentSchema] = Field(default_factory=list, max_length=100)
    interest_rate_changes: list[InterestRateChangeSchema] = Field(default_factory=list, max_length=100)


class CreatePlanRequest(AdjustmentsSchema):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(ge=0, le=100)
    term: TermSchema
    start_date: datetime.date | None = None
    loan_type: LoanType = LoanType.Other
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    lender: str | None = Field(default=None, max_length=200)
    upfront_fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    early_payment_fees: EarlyPaymentFeesSchema = Field(default_factory=EarlyPaymentFeesSchema)
    housing_costs: HousingCostsSchema | None = None
    interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth


class UpdatePlanRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Decimal | None = Field(default=None, gt=0)
    interest_rate: Decimal | None = Field(default=None, ge=0, le=100)
    term: TermSchema | None = None
    start_date: datetime.date | None = None
    loan_type: LoanType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    lender: str | None = Field(default=None, max_length=200)
    upfront_fees: Decimal | None = Field(default=None, ge=0)
    early_payment_fees: EarlyPaymentFeesSchema | None = None
    housing_costs: HousingCostsSchema | None = None
    interest_rate_application: InterestRateApplication | None = None


class AddExtraPaymentRequest(BaseModel):
    date: datetime.date
    amount: Decimal = Field(gt=0)


class AddRecurringExtraPaymentRequest(BaseModel):
    start_date: datetime.date
    amount: Decimal = Field(gt=0)
    count: int = Field(gt=0, le=600)


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
    loan_type: LoanType
    currency: str
    lender: str | None
    upfront_fees: Decimal
    early_payment_fees: EarlyPaymentFeesSchema
    housing_costs: HousingCostsSchema
    down_payment: Decimal | None
    ltv: Decimal | None
    monthly_payment: Decimal
    monthly_housing: HousingPaymentSchema | None
    interest_rate_application: str
    status: str
    one_time_extra_payments: list[ExtraPaymentSchema]
    recurring_extra_payments: list[RecurringExtraPaymentSchema]
    interest_rate_changes: list[InterestRateChangeSchema]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_entity(cls, plan: Plan) -> "PlanResponse":
        ltv = plan.housing_costs.ltv_percent(plan.amount)
        housing = plan.starting_housing_payment
        return cls(
            id=plan.id,
            user_id=plan.user_id,
            name=plan.name,
            slug=plan.slug,
            amount=plan.amount,
            interest_rate=plan.interest_rate,
            term=TermSchema(years=plan.term.years, months=plan.term.months),
            start_date=plan.start_date,
            loan_type=plan.loan_type,
            currency=plan.currency,
            lender=plan.lender,
            upfront_fees=plan.upfront_fees,
            early_payment_fees=EarlyPaymentFeesSchema(
                fixed=Decimal(plan.early_payment_fees.fixed),
                percent=Decimal(plan.early_payment_fees.percent),
            ),
            housing_costs=HousingCostsSchema.from_value(plan.housing_costs),
            down_payment=plan.housing_costs.down_payment(plan.amount),
            ltv=None if ltv is None else ltv.quantize(CENT),
            monthly_payment=plan.monthly_payment.quantize(CENT),
            monthly_housing=None if housing is None else HousingPaymentSchema.from_value(housing),
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
