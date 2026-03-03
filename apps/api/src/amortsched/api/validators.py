"""Mashumaro request/response schemas for the Starlette API."""

import datetime
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin


def _decimal_serializer(value: Decimal) -> str:
    return f"{value:.2f}"


class SchemaConfig(BaseConfig):
    serialization_strategy = {Decimal: {"serialize": _decimal_serializer, "deserialize": Decimal}}


# ── Auth ──────────────────────────────────────────────────────────────


@dataclass
class RegisterRequest(DataClassORJSONMixin):
    email: str
    name: str
    password: str


@dataclass
class LoginRequest(DataClassORJSONMixin):
    email: str
    password: str


@dataclass
class UserResponse(DataClassORJSONMixin):
    id: uuid.UUID
    email: str
    name: str
    is_active: bool

    class Config(SchemaConfig):
        aliases = {"is_active": "isActive"}
        serialize_by_alias = True


@dataclass
class AuthResponse(DataClassORJSONMixin):
    user: UserResponse
    token: str

    class Config(SchemaConfig):
        serialize_by_alias = True


# ── Profile ───────────────────────────────────────────────────────────


@dataclass
class UpsertProfileRequest(DataClassORJSONMixin):
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None

    class Config(SchemaConfig):
        aliases = {"display_name": "displayName"}
        allow_deserialization_not_by_alias = True


@dataclass
class ProfileResponse(DataClassORJSONMixin):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None
    phone: str | None
    locale: str | None
    timezone: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config(SchemaConfig):
        aliases = {
            "user_id": "userId",
            "display_name": "displayName",
            "created_at": "createdAt",
            "updated_at": "updatedAt",
        }
        serialize_by_alias = True


# ── Plan ──────────────────────────────────────────────────────────────


@dataclass
class TermSchema(DataClassORJSONMixin):
    years: int = 0
    months: int = 0


@dataclass
class EarlyPaymentFeesSchema(DataClassORJSONMixin):
    fixed: Decimal = Decimal("0.00")
    percent: Decimal = Decimal("0.00")

    class Config(SchemaConfig):
        serialize_by_alias = True


@dataclass
class ExtraPaymentSchema(DataClassORJSONMixin):
    date: datetime.date
    amount: Decimal

    class Config(SchemaConfig):
        serialize_by_alias = True


@dataclass
class RecurringExtraPaymentSchema(DataClassORJSONMixin):
    start_date: datetime.date
    amount: Decimal
    count: int

    class Config(SchemaConfig):
        aliases = {"start_date": "startDate"}
        allow_deserialization_not_by_alias = True
        serialize_by_alias = True


@dataclass
class InterestRateChangeSchema(DataClassORJSONMixin):
    effective_date: datetime.date
    yearly_interest_rate: Decimal

    class Config(SchemaConfig):
        aliases = {
            "effective_date": "effectiveDate",
            "yearly_interest_rate": "yearlyInterestRate",
        }
        allow_deserialization_not_by_alias = True
        serialize_by_alias = True


@dataclass
class CreatePlanRequest(DataClassORJSONMixin):
    name: str
    amount: Decimal
    interest_rate: Decimal
    term: TermSchema
    start_date: datetime.date = field(default_factory=datetime.date.today)
    early_payment_fees: EarlyPaymentFeesSchema = field(default_factory=EarlyPaymentFeesSchema)
    interest_rate_application: str = "whole_month"

    class Config(SchemaConfig):
        aliases = {
            "interest_rate": "interestRate",
            "start_date": "startDate",
            "early_payment_fees": "earlyPaymentFees",
            "interest_rate_application": "interestRateApplication",
        }
        allow_deserialization_not_by_alias = True


@dataclass
class UpdatePlanRequest(DataClassORJSONMixin):
    name: str | None = None
    amount: Decimal | None = None
    interest_rate: Decimal | None = None
    term: TermSchema | None = None
    start_date: datetime.date | None = None
    early_payment_fees: EarlyPaymentFeesSchema | None = None
    interest_rate_application: str | None = None

    class Config(SchemaConfig):
        aliases = {
            "interest_rate": "interestRate",
            "start_date": "startDate",
            "early_payment_fees": "earlyPaymentFees",
            "interest_rate_application": "interestRateApplication",
        }
        allow_deserialization_not_by_alias = True


@dataclass
class AddExtraPaymentRequest(DataClassORJSONMixin):
    date: datetime.date
    amount: Decimal


@dataclass
class AddRecurringExtraPaymentRequest(DataClassORJSONMixin):
    start_date: datetime.date
    amount: Decimal
    count: int

    class Config(SchemaConfig):
        aliases = {"start_date": "startDate"}
        allow_deserialization_not_by_alias = True


@dataclass
class AddInterestRateChangeRequest(DataClassORJSONMixin):
    effective_date: datetime.date
    rate: Decimal

    class Config(SchemaConfig):
        aliases = {"effective_date": "effectiveDate"}
        allow_deserialization_not_by_alias = True


@dataclass
class PlanResponse(DataClassORJSONMixin):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    slug: str
    amount: Decimal
    term: TermSchema
    interest_rate: Decimal
    start_date: datetime.date
    early_payment_fees: EarlyPaymentFeesSchema
    interest_rate_application: str
    status: str
    one_time_extra_payments: list[ExtraPaymentSchema]
    recurring_extra_payments: list[RecurringExtraPaymentSchema]
    interest_rate_changes: list[InterestRateChangeSchema]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config(SchemaConfig):
        aliases = {
            "user_id": "userId",
            "interest_rate": "interestRate",
            "start_date": "startDate",
            "early_payment_fees": "earlyPaymentFees",
            "interest_rate_application": "interestRateApplication",
            "one_time_extra_payments": "oneTimeExtraPayments",
            "recurring_extra_payments": "recurringExtraPayments",
            "interest_rate_changes": "interestRateChanges",
            "created_at": "createdAt",
            "updated_at": "updatedAt",
        }
        serialize_by_alias = True


# ── Schedule ──────────────────────────────────────────────────────────


@dataclass
class BalanceResponse(DataClassORJSONMixin):
    before: Decimal
    after: Decimal

    class Config(SchemaConfig):
        serialize_by_alias = True


@dataclass
class InstallmentResponse(DataClassORJSONMixin):
    installment: int | None
    year: int
    month: int
    month_name: str
    type: str
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    balance: BalanceResponse

    class Config(SchemaConfig):
        aliases = {"month_name": "monthName"}
        serialize_by_alias = True


@dataclass
class TotalsResponse(DataClassORJSONMixin):
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    months: int
    paid_off: bool

    class Config(SchemaConfig):
        aliases = {"paid_off": "paidOff"}
        serialize_by_alias = True


@dataclass
class ScheduleResponse(DataClassORJSONMixin):
    id: uuid.UUID
    plan_id: uuid.UUID
    generated_at: datetime.datetime
    installments: list[InstallmentResponse]
    totals: TotalsResponse | None = None

    class Config(SchemaConfig):
        aliases = {
            "plan_id": "planId",
            "generated_at": "generatedAt",
        }
        serialize_by_alias = True
