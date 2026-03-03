"""Pydantic v2 request/response models for the FastAPI app."""

import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ── Auth ──────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    is_active: bool = Field(alias="isActive")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AuthResponse(BaseModel):
    user: UserResponse
    token: str


# ── Profile ───────────────────────────────────────────────────────────


class UpsertProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, alias="displayName")
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID = Field(alias="userId")
    display_name: str | None = Field(alias="displayName")
    phone: str | None
    locale: str | None
    timezone: str | None
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# ── Plan ──────────────────────────────────────────────────────────────


class Term(BaseModel):
    years: int = 0
    months: int = 0


class EarlyPaymentFees(BaseModel):
    fixed: Decimal = Decimal("0.00")
    percent: Decimal = Decimal("0.00")


class ExtraPayment(BaseModel):
    date: datetime.date
    amount: Decimal


class RecurringExtraPayment(BaseModel):
    start_date: datetime.date = Field(alias="startDate")
    amount: Decimal
    count: int

    model_config = ConfigDict(populate_by_name=True)


class InterestRateChange(BaseModel):
    effective_date: datetime.date = Field(alias="effectiveDate")
    yearly_interest_rate: Decimal = Field(alias="yearlyInterestRate")

    model_config = ConfigDict(populate_by_name=True)


class CreatePlanRequest(BaseModel):
    name: str
    amount: Decimal
    interest_rate: Decimal = Field(alias="interestRate")
    term: Term
    start_date: datetime.date = Field(default_factory=datetime.date.today, alias="startDate")
    early_payment_fees: EarlyPaymentFees = Field(default_factory=EarlyPaymentFees, alias="earlyPaymentFees")
    interest_rate_application: str = Field(default="whole_month", alias="interestRateApplication")

    model_config = ConfigDict(populate_by_name=True)


class UpdatePlanRequest(BaseModel):
    name: str | None = None
    amount: Decimal | None = None
    interest_rate: Decimal | None = Field(default=None, alias="interestRate")
    term: Term | None = None
    start_date: datetime.date | None = Field(default=None, alias="startDate")
    early_payment_fees: EarlyPaymentFees | None = Field(default=None, alias="earlyPaymentFees")
    interest_rate_application: str | None = Field(default=None, alias="interestRateApplication")

    model_config = ConfigDict(populate_by_name=True)


class AddExtraPaymentRequest(BaseModel):
    date: datetime.date
    amount: Decimal


class AddRecurringExtraPaymentRequest(BaseModel):
    start_date: datetime.date = Field(alias="startDate")
    amount: Decimal
    count: int

    model_config = ConfigDict(populate_by_name=True)


class AddInterestRateChangeRequest(BaseModel):
    effective_date: datetime.date = Field(alias="effectiveDate")
    rate: Decimal

    model_config = ConfigDict(populate_by_name=True)


class PlanResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID = Field(alias="userId")
    name: str
    slug: str
    amount: Decimal
    term: Term
    interest_rate: Decimal = Field(alias="interestRate")
    start_date: datetime.date = Field(alias="startDate")
    early_payment_fees: EarlyPaymentFees = Field(alias="earlyPaymentFees")
    interest_rate_application: str = Field(alias="interestRateApplication")
    status: str
    one_time_extra_payments: list[ExtraPayment] = Field(alias="oneTimeExtraPayments")
    recurring_extra_payments: list[RecurringExtraPayment] = Field(alias="recurringExtraPayments")
    interest_rate_changes: list[InterestRateChange] = Field(alias="interestRateChanges")
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# ── Schedule ──────────────────────────────────────────────────────────


class Balance(BaseModel):
    before: Decimal
    after: Decimal


class InstallmentResponse(BaseModel):
    installment: int | None
    year: int
    month: int
    month_name: str = Field(alias="monthName")
    type: str
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    balance: Balance

    model_config = ConfigDict(populate_by_name=True)


class TotalsResponse(BaseModel):
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    months: int
    paid_off: bool = Field(alias="paidOff")

    model_config = ConfigDict(populate_by_name=True)


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID = Field(alias="planId")
    generated_at: datetime.datetime = Field(alias="generatedAt")
    installments: list[InstallmentResponse]
    totals: TotalsResponse | None = None

    model_config = ConfigDict(populate_by_name=True)
