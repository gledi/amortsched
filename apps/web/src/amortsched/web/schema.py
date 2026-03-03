"""Strawberry GraphQL schema with full queries and mutations."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

import strawberry
from starlette.requests import Request
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from amortsched.app.plans import (
    AddInterestRateChangeCommand,
    AddOneTimeExtraPaymentCommand,
    AddRecurringExtraPaymentCommand,
    CreatePlanCommand,
    DeletePlanCommand,
    DeleteScheduleCommand,
    GenerateScheduleQuery,
    GetPlanQuery,
    GetScheduleQuery,
    ListPlansQuery,
    ListSchedulesQuery,
    SavePlanCommand,
    SaveScheduleCommand,
    UpdatePlanCommand,
)
from amortsched.app.users import (
    AuthenticateUserCommand,
    GetProfileQuery,
    GetUserQuery,
    RegisterUserCommand,
    UpsertProfileCommand,
)
from amortsched.core.errors import InvalidTokenError
from amortsched.core.values import EarlyPaymentFees as DomainEarlyPaymentFees
from amortsched.core.values import InterestRateApplication
from amortsched.web.deps import (
    get_add_interest_rate_change_handler,
    get_add_one_time_extra_payment_handler,
    get_add_recurring_extra_payment_handler,
    get_authenticate_user_handler,
    get_create_plan_handler,
    get_delete_plan_handler,
    get_delete_schedule_handler,
    get_generate_schedule_handler,
    get_list_plans_handler,
    get_list_schedules_handler,
    get_plan_handler,
    get_profile_handler,
    get_register_user_handler,
    get_save_plan_handler,
    get_save_schedule_handler,
    get_schedule_handler,
    get_token_service,
    get_update_plan_handler,
    get_upsert_profile_handler,
    get_user_handler,
)

# ── Helper ────────────────────────────────────────────────────────────


def _get_user_id(info: Info) -> uuid.UUID:
    """Extract authenticated user_id from context. Raises InvalidTokenError if missing."""
    user_id = info.context.get("user_id")
    if user_id is None:
        raise InvalidTokenError("Authentication required")
    return user_id


# ── Strawberry Types ──────────────────────────────────────────────────


@strawberry.type
@dataclass
class UserType:
    id: strawberry.ID
    email: str
    name: str
    is_active: bool


@strawberry.type
@dataclass
class AuthPayload:
    user: UserType
    token: str


@strawberry.type
@dataclass
class ProfileType:
    id: strawberry.ID
    user_id: strawberry.ID
    display_name: str | None
    phone: str | None
    locale: str | None
    timezone: str | None
    created_at: str
    updated_at: str


@strawberry.type
@dataclass
class TermType:
    years: int
    months: int


@strawberry.type
@dataclass
class EarlyPaymentFeesType:
    fixed: str
    percent: str


@strawberry.type
@dataclass
class ExtraPaymentType:
    date: str
    amount: str


@strawberry.type
@dataclass
class RecurringExtraPaymentType:
    start_date: str
    amount: str
    count: int


@strawberry.type
@dataclass
class InterestRateChangeType:
    effective_date: str
    yearly_interest_rate: str


@strawberry.type
@dataclass
class PlanType:
    id: strawberry.ID
    user_id: strawberry.ID
    name: str
    slug: str
    amount: str
    term: TermType
    interest_rate: str
    start_date: str
    early_payment_fees: EarlyPaymentFeesType
    interest_rate_application: str
    status: str
    one_time_extra_payments: list[ExtraPaymentType]
    recurring_extra_payments: list[RecurringExtraPaymentType]
    interest_rate_changes: list[InterestRateChangeType]
    created_at: str
    updated_at: str


@strawberry.type
@dataclass
class BalanceType:
    before: str
    after: str


@strawberry.type
@dataclass
class InstallmentType:
    installment: int | None
    year: int
    month: int
    month_name: str
    type: str
    principal: str
    interest: str
    fees: str
    total: str
    balance: BalanceType


@strawberry.type
@dataclass
class TotalsType:
    principal: str
    interest: str
    fees: str
    total: str
    months: int
    paid_off: bool


@strawberry.type
@dataclass
class ScheduleType:
    id: strawberry.ID
    plan_id: strawberry.ID
    generated_at: str
    installments: list[InstallmentType]
    totals: TotalsType | None


# ── Inputs ────────────────────────────────────────────────────────────


@strawberry.input
class RegisterInput:
    email: str
    name: str
    password: str


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class ProfileInput:
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None


@strawberry.input
class CreatePlanInput:
    name: str
    amount: str
    interest_rate: str
    term_years: int = 0
    term_months: int = 0
    start_date: str | None = None
    early_payment_fees_fixed: str = "0.00"
    early_payment_fees_percent: str = "0.00"
    interest_rate_application: str = "whole_month"


@strawberry.input
class UpdatePlanInput:
    name: str | None = None
    amount: str | None = None
    interest_rate: str | None = None
    term_years: int | None = None
    term_months: int | None = None
    start_date: str | None = None
    early_payment_fees_fixed: str | None = None
    early_payment_fees_percent: str | None = None
    interest_rate_application: str | None = None


@strawberry.input
class ExtraPaymentInput:
    date: str
    amount: str


@strawberry.input
class RecurringExtraPaymentInput:
    start_date: str
    amount: str
    count: int


@strawberry.input
class InterestRateChangeInput:
    effective_date: str
    rate: str


# ── Converters ────────────────────────────────────────────────────────


def _user_to_type(user) -> UserType:
    return UserType(
        id=strawberry.ID(str(user.id)),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
    )


def _profile_to_type(profile) -> ProfileType:
    return ProfileType(
        id=strawberry.ID(str(profile.id)),
        user_id=strawberry.ID(str(profile.user_id)),
        display_name=profile.display_name,
        phone=profile.phone,
        locale=profile.locale,
        timezone=profile.timezone,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


def _plan_to_type(plan) -> PlanType:
    return PlanType(
        id=strawberry.ID(str(plan.id)),
        user_id=strawberry.ID(str(plan.user_id)),
        name=plan.name,
        slug=plan.slug,
        amount=f"{plan.amount:.2f}",
        term=TermType(years=plan.term.years, months=plan.term.months),
        interest_rate=f"{plan.interest_rate:.2f}",
        start_date=plan.start_date.isoformat(),
        early_payment_fees=EarlyPaymentFeesType(
            fixed=f"{plan.early_payment_fees.fixed:.2f}",
            percent=f"{plan.early_payment_fees.percent:.2f}",
        ),
        interest_rate_application=plan.interest_rate_application.value,
        status=plan.status.value,
        one_time_extra_payments=[
            ExtraPaymentType(date=ep.date.isoformat(), amount=f"{ep.amount:.2f}") for ep in plan.one_time_extra_payments
        ],
        recurring_extra_payments=[
            RecurringExtraPaymentType(start_date=rp.start_date.isoformat(), amount=f"{rp.amount:.2f}", count=rp.count)
            for rp in plan.recurring_extra_payments
        ],
        interest_rate_changes=[
            InterestRateChangeType(
                effective_date=rc.effective_date.isoformat(),
                yearly_interest_rate=f"{rc.yearly_interest_rate:.2f}",
            )
            for rc in plan.interest_rate_changes
        ],
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


def _schedule_to_type(schedule) -> ScheduleType:
    installments = [
        InstallmentType(
            installment=item.i,
            year=item.year,
            month=item.month.value,
            month_name=item.month_name,
            type=item.payment.kind,
            principal=f"{item.payment.principal:.2f}",
            interest=f"{item.payment.interest:.2f}",
            fees=f"{item.payment.fees:.2f}",
            total=f"{item.payment.total:.2f}",
            balance=BalanceType(before=f"{item.balance.before:.2f}", after=f"{item.balance.after:.2f}"),
        )
        for item in schedule.installments
    ]
    totals = None
    if schedule.totals is not None:
        totals = TotalsType(
            principal=f"{schedule.totals.principal:.2f}",
            interest=f"{schedule.totals.interest:.2f}",
            fees=f"{schedule.totals.fees:.2f}",
            total=f"{schedule.totals.total_outflow:.2f}",
            months=schedule.totals.months,
            paid_off=schedule.totals.paid_off,
        )
    return ScheduleType(
        id=strawberry.ID(str(schedule.id)),
        plan_id=strawberry.ID(str(schedule.plan_id)),
        generated_at=schedule.generated_at.isoformat(),
        installments=installments,
        totals=totals,
    )


# ── Query ─────────────────────────────────────────────────────────────


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> UserType:
        user_id = _get_user_id(info)
        handler = get_user_handler()
        user = handler.handle(GetUserQuery(user_id=user_id))
        return _user_to_type(user)

    @strawberry.field
    def my_profile(self, info: Info) -> ProfileType | None:
        user_id = _get_user_id(info)
        handler = get_profile_handler()
        try:
            profile = handler.handle(GetProfileQuery(user_id=user_id))
        except Exception:
            return None
        return _profile_to_type(profile)

    @strawberry.field
    def plan(self, info: Info, plan_id: strawberry.ID) -> PlanType:
        user_id = _get_user_id(info)
        handler = get_plan_handler()
        plan = handler.handle(GetPlanQuery(plan_id=uuid.UUID(str(plan_id)), user_id=user_id))
        return _plan_to_type(plan)

    @strawberry.field
    def plans(self, info: Info) -> list[PlanType]:
        user_id = _get_user_id(info)
        handler = get_list_plans_handler()
        plans = handler.handle(ListPlansQuery(user_id=user_id))
        return [_plan_to_type(p) for p in plans]

    @strawberry.field
    def schedule(self, info: Info, schedule_id: strawberry.ID) -> ScheduleType:
        user_id = _get_user_id(info)
        handler = get_schedule_handler()
        schedule = handler.handle(GetScheduleQuery(schedule_id=uuid.UUID(str(schedule_id)), user_id=user_id))
        return _schedule_to_type(schedule)

    @strawberry.field
    def schedules(self, info: Info, plan_id: strawberry.ID) -> list[ScheduleType]:
        user_id = _get_user_id(info)
        handler = get_list_schedules_handler()
        schedules = handler.handle(ListSchedulesQuery(plan_id=uuid.UUID(str(plan_id)), user_id=user_id))
        return [_schedule_to_type(s) for s in schedules]


# ── Mutation ──────────────────────────────────────────────────────────


@strawberry.type
class Mutation:
    @strawberry.mutation
    def register(self, input: RegisterInput) -> AuthPayload:
        handler = get_register_user_handler()
        token_service = get_token_service()
        user = handler.handle(RegisterUserCommand(email=input.email, name=input.name, password=input.password))
        token = token_service.create_access_token(user.id)
        return AuthPayload(user=_user_to_type(user), token=token)

    @strawberry.mutation
    def login(self, input: LoginInput) -> AuthPayload:
        handler = get_authenticate_user_handler()
        token_service = get_token_service()
        user = handler.handle(AuthenticateUserCommand(email=input.email, password=input.password))
        token = token_service.create_access_token(user.id)
        return AuthPayload(user=_user_to_type(user), token=token)

    @strawberry.mutation
    def upsert_profile(self, info: Info, input: ProfileInput) -> ProfileType:
        user_id = _get_user_id(info)
        handler = get_upsert_profile_handler()
        profile = handler.handle(
            UpsertProfileCommand(
                user_id=user_id,
                display_name=input.display_name,
                phone=input.phone,
                locale=input.locale,
                timezone=input.timezone,
            )
        )
        return _profile_to_type(profile)

    @strawberry.mutation
    def create_plan(self, info: Info, input: CreatePlanInput) -> PlanType:
        import datetime

        user_id = _get_user_id(info)
        handler = get_create_plan_handler()
        start_date = datetime.date.fromisoformat(input.start_date) if input.start_date else datetime.date.today()
        early_fees = DomainEarlyPaymentFees(
            fixed=Decimal(input.early_payment_fees_fixed),
            percent=Decimal(input.early_payment_fees_percent),
        )
        plan = handler.handle(
            CreatePlanCommand(
                user_id=user_id,
                name=input.name,
                amount=Decimal(input.amount),
                term=(input.term_years, input.term_months),
                interest_rate=Decimal(input.interest_rate),
                start_date=start_date,
                early_payment_fees=early_fees,
                interest_rate_application=InterestRateApplication(input.interest_rate_application),
            )
        )
        return _plan_to_type(plan)

    @strawberry.mutation
    def update_plan(self, info: Info, plan_id: strawberry.ID, input: UpdatePlanInput) -> PlanType:
        import datetime

        user_id = _get_user_id(info)
        handler = get_update_plan_handler()
        early_fees = None
        if input.early_payment_fees_fixed is not None and input.early_payment_fees_percent is not None:
            early_fees = DomainEarlyPaymentFees(
                fixed=Decimal(input.early_payment_fees_fixed),
                percent=Decimal(input.early_payment_fees_percent),
            )
        term = None
        if input.term_years is not None and input.term_months is not None:
            term = (input.term_years, input.term_months)
        start_date = datetime.date.fromisoformat(input.start_date) if input.start_date else None
        ira = InterestRateApplication(input.interest_rate_application) if input.interest_rate_application else None
        plan = handler.handle(
            UpdatePlanCommand(
                plan_id=uuid.UUID(str(plan_id)),
                user_id=user_id,
                name=input.name,
                amount=Decimal(input.amount) if input.amount else None,
                term=term,
                interest_rate=Decimal(input.interest_rate) if input.interest_rate else None,
                start_date=start_date,
                early_payment_fees=early_fees,
                interest_rate_application=ira,
            )
        )
        return _plan_to_type(plan)

    @strawberry.mutation
    def delete_plan(self, info: Info, plan_id: strawberry.ID) -> bool:
        user_id = _get_user_id(info)
        handler = get_delete_plan_handler()
        handler.handle(DeletePlanCommand(plan_id=uuid.UUID(str(plan_id)), user_id=user_id))
        return True

    @strawberry.mutation
    def save_plan(self, info: Info, plan_id: strawberry.ID) -> PlanType:
        user_id = _get_user_id(info)
        handler = get_save_plan_handler()
        plan = handler.handle(SavePlanCommand(plan_id=uuid.UUID(str(plan_id)), user_id=user_id))
        return _plan_to_type(plan)

    @strawberry.mutation
    def add_extra_payment(self, info: Info, plan_id: strawberry.ID, input: ExtraPaymentInput) -> PlanType:
        import datetime

        user_id = _get_user_id(info)
        handler = get_add_one_time_extra_payment_handler()
        plan = handler.handle(
            AddOneTimeExtraPaymentCommand(
                plan_id=uuid.UUID(str(plan_id)),
                user_id=user_id,
                date=datetime.date.fromisoformat(input.date),
                amount=Decimal(input.amount),
            )
        )
        return _plan_to_type(plan)

    @strawberry.mutation
    def add_recurring_extra_payment(
        self, info: Info, plan_id: strawberry.ID, input: RecurringExtraPaymentInput
    ) -> PlanType:
        import datetime

        user_id = _get_user_id(info)
        handler = get_add_recurring_extra_payment_handler()
        plan = handler.handle(
            AddRecurringExtraPaymentCommand(
                plan_id=uuid.UUID(str(plan_id)),
                user_id=user_id,
                start_date=datetime.date.fromisoformat(input.start_date),
                amount=Decimal(input.amount),
                count=input.count,
            )
        )
        return _plan_to_type(plan)

    @strawberry.mutation
    def add_interest_rate_change(self, info: Info, plan_id: strawberry.ID, input: InterestRateChangeInput) -> PlanType:
        import datetime

        user_id = _get_user_id(info)
        handler = get_add_interest_rate_change_handler()
        plan = handler.handle(
            AddInterestRateChangeCommand(
                plan_id=uuid.UUID(str(plan_id)),
                user_id=user_id,
                effective_date=datetime.date.fromisoformat(input.effective_date),
                rate=Decimal(input.rate),
            )
        )
        return _plan_to_type(plan)

    @strawberry.mutation
    def preview_schedule(self, info: Info, plan_id: strawberry.ID) -> ScheduleType:
        user_id = _get_user_id(info)
        handler = get_generate_schedule_handler()
        schedule = handler.handle(GenerateScheduleQuery(plan_id=uuid.UUID(str(plan_id)), user_id=user_id))
        return _schedule_to_type(schedule)

    @strawberry.mutation
    def save_schedule(self, info: Info, plan_id: strawberry.ID) -> ScheduleType:
        user_id = _get_user_id(info)
        handler = get_save_schedule_handler()
        schedule = handler.handle(SaveScheduleCommand(plan_id=uuid.UUID(str(plan_id)), user_id=user_id))
        return _schedule_to_type(schedule)

    @strawberry.mutation
    def delete_schedule(self, info: Info, schedule_id: strawberry.ID) -> bool:
        user_id = _get_user_id(info)
        handler = get_delete_schedule_handler()
        handler.handle(DeleteScheduleCommand(schedule_id=uuid.UUID(str(schedule_id)), user_id=user_id))
        return True


# ── Context + Router ──────────────────────────────────────────────────


async def get_context(request: Request) -> dict:
    """Extract user_id from Authorization header if present."""
    context: dict = {}
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")
        token_service = get_token_service()
        try:
            user_id = token_service.decode_access_token(token)
            context["user_id"] = user_id
        except Exception:
            pass
    return context


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=get_context)
