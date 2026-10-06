import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from amortsched.app.access import get_owned_plan, get_owned_schedule
from amortsched.core.entities import Plan, Profile, Schedule
from amortsched.core.errors import ValidationError
from amortsched.core.repositories import AsyncRepository
from amortsched.core.specifications import Eq, Id
from amortsched.core.values import (
    DEFAULT_CURRENCY,
    Amount,
    EarlyPaymentFees,
    HousingCosts,
    InterestRate,
    InterestRateApplication,
    InterestRateChange,
    LoanType,
    OneTimeExtraPayment,
    RecurringExtraPayment,
    Term,
    TermType,
    normalize_currency,
)

_get_owned_plan = get_owned_plan
_get_owned_schedule = get_owned_schedule


def _validate_upfront_fees(upfront_fees: Decimal) -> Decimal:
    fees = Decimal(upfront_fees)
    if fees < 0:
        raise ValidationError([{"field": "upfront_fees", "message": "Upfront fees must be zero or greater"}])
    return fees


def _apply_offer_fields(plan: Plan, lender: str | None, upfront_fees: Decimal | None) -> None:
    if lender is not None:
        plan.lender = lender.strip() or None
    if upfront_fees is not None:
        plan.upfront_fees = _validate_upfront_fees(upfront_fees)


def _to_term(term: TermType) -> Term:
    if isinstance(term, int):
        return Term(term, 0)
    if isinstance(term, tuple):
        return Term(*term)
    return term


def _apply_loan_fields(plan: Plan, command: "UpdatePlanCommand") -> None:
    if command.loan_type is not None:
        plan.loan_type = command.loan_type
    if command.currency is not None:
        plan.currency = normalize_currency(command.currency)
    if command.housing_costs is not None:
        plan.housing_costs = command.housing_costs
    if command.amount is not None:
        plan.amount = Decimal(command.amount)
    if command.term is not None:
        plan.term = _to_term(command.term)
    if command.interest_rate is not None:
        plan.interest_rate = Decimal(command.interest_rate)
    if command.start_date is not None:
        plan.start_date = command.start_date


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def _sorted_rate_changes(changes: list[InterestRateChange]) -> list[InterestRateChange]:
    return sorted(changes, key=lambda change: change.effective_date)


@dataclass(frozen=True, slots=True)
class CreatePlanCommand:
    user_id: uuid.UUID
    name: str
    amount: Amount
    term: TermType
    interest_rate: InterestRate
    start_date: datetime.date
    loan_type: LoanType = LoanType.Other
    currency: str | None = None
    lender: str | None = None
    upfront_fees: Decimal | None = None
    early_payment_fees: EarlyPaymentFees | None = None
    housing_costs: HousingCosts | None = None
    interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth
    one_time_extra_payments: tuple[OneTimeExtraPayment, ...] = ()
    recurring_extra_payments: tuple[RecurringExtraPayment, ...] = ()
    interest_rate_changes: tuple[InterestRateChange, ...] = ()


class CreatePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan], profile_repo: AsyncRepository[Profile] | None = None) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo
        self._profile_repo: AsyncRepository[Profile] | None = profile_repo

    async def _default_currency(self, user_id: uuid.UUID) -> str:
        if self._profile_repo is None:
            return DEFAULT_CURRENCY
        profile = await self._profile_repo.get_one_or_none(Eq("user_id", user_id))
        return profile.currency if profile is not None and profile.currency else DEFAULT_CURRENCY

    async def handle(self, command: CreatePlanCommand) -> Plan:
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        interest_rate = (
            command.interest_rate if isinstance(command.interest_rate, Decimal) else Decimal(command.interest_rate)
        )
        term = _to_term(command.term)
        lender = (command.lender.strip() or None) if command.lender is not None else None
        upfront_fees = _validate_upfront_fees(
            Decimal("0.00") if command.upfront_fees is None else Decimal(command.upfront_fees)
        )
        currency = (
            normalize_currency(command.currency) if command.currency else await self._default_currency(command.user_id)
        )
        plan = Plan(
            user_id=command.user_id,
            name=command.name,
            slug=_slugify(command.name),
            amount=amount,
            term=term,
            interest_rate=interest_rate,
            start_date=command.start_date,
            loan_type=command.loan_type,
            currency=currency,
            lender=lender,
            upfront_fees=upfront_fees,
            early_payment_fees=command.early_payment_fees
            if command.early_payment_fees is not None
            else EarlyPaymentFees(),
            housing_costs=command.housing_costs if command.housing_costs is not None else HousingCosts(),
            interest_rate_application=command.interest_rate_application,
            one_time_extra_payments=list(command.one_time_extra_payments),
            recurring_extra_payments=list(command.recurring_extra_payments),
            interest_rate_changes=_sorted_rate_changes(list(command.interest_rate_changes)),
        )
        _ = await self._plan_repo.add(plan)
        return plan


@dataclass(frozen=True, slots=True)
class UpdatePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    name: str | None = None
    amount: Amount | None = None
    term: TermType | None = None
    interest_rate: InterestRate | None = None
    start_date: datetime.date | None = None
    loan_type: LoanType | None = None
    currency: str | None = None
    lender: str | None = None
    upfront_fees: Decimal | None = None
    early_payment_fees: EarlyPaymentFees | None = None
    housing_costs: HousingCosts | None = None
    interest_rate_application: InterestRateApplication | None = None


class UpdatePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: UpdatePlanCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        if command.name is not None:
            plan.name = command.name
            plan.slug = _slugify(command.name)
        _apply_loan_fields(plan, command)
        _apply_offer_fields(plan, command.lender, command.upfront_fees)
        if command.early_payment_fees is not None:
            plan.early_payment_fees = command.early_payment_fees
        if command.interest_rate_application is not None:
            plan.interest_rate_application = command.interest_rate_application
        plan.touch()
        _ = await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class ReplaceAdjustmentsCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    one_time_extra_payments: tuple[OneTimeExtraPayment, ...]
    recurring_extra_payments: tuple[RecurringExtraPayment, ...]
    interest_rate_changes: tuple[InterestRateChange, ...]


class ReplaceAdjustmentsHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: ReplaceAdjustmentsCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        plan.one_time_extra_payments = list(command.one_time_extra_payments)
        plan.recurring_extra_payments = list(command.recurring_extra_payments)
        plan.interest_rate_changes = _sorted_rate_changes(list(command.interest_rate_changes))
        plan.touch()
        _ = await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class DuplicatePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class DuplicatePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: DuplicatePlanCommand) -> Plan:
        source = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        name = f"{source.name} (copy)"
        copy = Plan(
            user_id=source.user_id,
            name=name,
            slug=_slugify(name),
            amount=source.amount,
            term=source.term,
            interest_rate=source.interest_rate,
            start_date=source.start_date,
            loan_type=source.loan_type,
            currency=source.currency,
            lender=source.lender,
            upfront_fees=source.upfront_fees,
            early_payment_fees=source.early_payment_fees,
            housing_costs=source.housing_costs,
            interest_rate_application=source.interest_rate_application,
            one_time_extra_payments=list(source.one_time_extra_payments),
            recurring_extra_payments=list(source.recurring_extra_payments),
            interest_rate_changes=list(source.interest_rate_changes),
        )
        _ = await self._plan_repo.add(copy)
        return copy


@dataclass(frozen=True, slots=True)
class DeletePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class DeletePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: DeletePlanCommand) -> None:
        _ = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        _ = await self._plan_repo.delete(Id(command.plan_id))


@dataclass(frozen=True, slots=True)
class SavePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class SavePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: SavePlanCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        plan.status = Plan.Status.Saved
        plan.touch()
        _ = await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class AddOneTimeExtraPaymentCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    date: datetime.date
    amount: Amount


class AddOneTimeExtraPaymentHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: AddOneTimeExtraPaymentCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        plan.one_time_extra_payments.append(OneTimeExtraPayment(date=command.date, amount=amount))
        plan.touch()
        _ = await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class AddRecurringExtraPaymentCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    start_date: datetime.date
    amount: Amount
    count: int


class AddRecurringExtraPaymentHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: AddRecurringExtraPaymentCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        plan.recurring_extra_payments.append(
            RecurringExtraPayment(start_date=command.start_date, amount=amount, count=command.count)
        )
        plan.touch()
        _ = await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class AddInterestRateChangeCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    effective_date: datetime.date
    rate: InterestRate


class AddInterestRateChangeHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: AddInterestRateChangeCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        rate = command.rate if isinstance(command.rate, Decimal) else Decimal(command.rate)
        plan.interest_rate_changes.append(
            InterestRateChange(effective_date=command.effective_date, yearly_interest_rate=rate)
        )
        plan.interest_rate_changes.sort(key=lambda c: c.effective_date)
        plan.touch()
        _ = await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class SaveScheduleCommand:
    plan_id: uuid.UUID
    schedule_id: uuid.UUID
    user_id: uuid.UUID


class SaveScheduleHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan], schedule_repo: AsyncRepository[Schedule]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo
        self._schedule_repo: AsyncRepository[Schedule] = schedule_repo

    async def handle(self, command: SaveScheduleCommand) -> Schedule:
        return await _get_owned_schedule(
            self._schedule_repo,
            self._plan_repo,
            command.schedule_id,
            command.plan_id,
            command.user_id,
        )


@dataclass(frozen=True, slots=True)
class DeleteScheduleCommand:
    schedule_id: uuid.UUID
    plan_id: uuid.UUID
    user_id: uuid.UUID


class DeleteScheduleHandler:
    def __init__(self, schedule_repo: AsyncRepository[Schedule], plan_repo: AsyncRepository[Plan]) -> None:
        self._schedule_repo: AsyncRepository[Schedule] = schedule_repo
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, command: DeleteScheduleCommand) -> None:
        _ = await _get_owned_schedule(
            self._schedule_repo, self._plan_repo, command.schedule_id, command.plan_id, command.user_id
        )
        _ = await self._schedule_repo.delete(Id(command.schedule_id))
