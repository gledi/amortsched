import datetime
import uuid
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RegisterRequest:
    email: str
    name: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginRequest:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class UserResponse:
    id: uuid.UUID
    email: str
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class AuthResponse:
    user: UserResponse
    token: str


@dataclass(frozen=True, slots=True)
class UpsertProfileRequest:
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None


@dataclass(frozen=True, slots=True)
class ProfileResponse:
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None
    phone: str | None
    locale: str | None
    timezone: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass(frozen=True, slots=True)
class TermSchema:
    years: int = 0
    months: int = 0


@dataclass(frozen=True, slots=True)
class EarlyPaymentFeesSchema:
    fixed: Decimal = Decimal("0.00")
    percent: Decimal = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class ExtraPaymentSchema:
    date: datetime.date
    amount: Decimal


@dataclass(frozen=True, slots=True)
class RecurringExtraPaymentSchema:
    start_date: datetime.date
    amount: Decimal
    count: int


@dataclass(frozen=True, slots=True)
class InterestRateChangeSchema:
    effective_date: datetime.date
    rate: Decimal


@dataclass(frozen=True, slots=True)
class CreatePlanRequest:
    name: str
    amount: Decimal
    interest_rate: Decimal
    term: TermSchema
    start_date: datetime.date | None = None
    early_payment_fees: EarlyPaymentFeesSchema = field(default_factory=EarlyPaymentFeesSchema)
    interest_rate_application: str = "whole_month"


@dataclass(frozen=True, slots=True)
class UpdatePlanRequest:
    name: str | None = None
    amount: Decimal | None = None
    interest_rate: Decimal | None = None
    term: TermSchema | None = None
    start_date: datetime.date | None = None
    early_payment_fees: EarlyPaymentFeesSchema | None = None
    interest_rate_application: str | None = None


@dataclass(frozen=True, slots=True)
class AddExtraPaymentRequest:
    date: datetime.date
    amount: Decimal


@dataclass(frozen=True, slots=True)
class AddRecurringExtraPaymentRequest:
    start_date: datetime.date
    amount: Decimal
    count: int


@dataclass(frozen=True, slots=True)
class AddInterestRateChangeRequest:
    effective_date: datetime.date
    rate: Decimal


@dataclass(frozen=True, slots=True)
class PlanResponse:
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


@dataclass(frozen=True, slots=True)
class BalanceSchema:
    before: Decimal
    after: Decimal


@dataclass(frozen=True, slots=True)
class InstallmentSchema:
    installment_number: int | None
    year: int
    month: int
    month_name: str
    type: str
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total: Decimal
    balance: BalanceSchema


@dataclass(frozen=True, slots=True)
class TotalsSchema:
    principal: Decimal
    interest: Decimal
    fees: Decimal
    total_outflow: Decimal
    months: int
    paid_off: bool


@dataclass(frozen=True, slots=True)
class ScheduleResponse:
    id: uuid.UUID
    plan_id: uuid.UUID
    installments: list[InstallmentSchema]
    totals: TotalsSchema | None
    generated_at: datetime.datetime
