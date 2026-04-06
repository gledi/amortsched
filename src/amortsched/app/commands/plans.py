import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from amortsched.core.entities import Plan, Schedule
from amortsched.core.errors import PlanNotFoundError, PlanOwnershipError, ScheduleNotFoundError
from amortsched.core.repositories import AsyncRepository
from amortsched.core.specifications import Id
from amortsched.core.values import (
    Amount,
    EarlyPaymentFees,
    InterestRate,
    InterestRateApplication,
    InterestRateChange,
    OneTimeExtraPayment,
    RecurringExtraPayment,
    Term,
    TermType,
)


async def _get_owned_plan(plan_repo: AsyncRepository[Plan], plan_id: uuid.UUID, user_id: uuid.UUID) -> Plan:
    """Fetch a plan and verify ownership.

    Raises:
        PlanNotFoundError: If the plan does not exist.
        PlanOwnershipError: If the plan belongs to a different user.
    """
    plan = await plan_repo.get_by_id(plan_id)
    if plan is None:
        raise PlanNotFoundError(plan_id)
    if plan.user_id != user_id:
        raise PlanOwnershipError(plan_id, user_id)
    return plan


async def _get_owned_schedule(
    schedule_repo: AsyncRepository[Schedule],
    plan_repo: AsyncRepository[Plan],
    schedule_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Schedule:
    """Fetch a schedule and verify ownership transitively through its plan.

    Raises:
        ScheduleNotFoundError: If the schedule does not exist.
        PlanNotFoundError: If the associated plan does not exist.
        PlanOwnershipError: If the plan belongs to a different user.
    """
    schedule = await schedule_repo.get_by_id(schedule_id)
    if schedule is None:
        raise ScheduleNotFoundError(schedule_id)
    plan = await _get_owned_plan(plan_repo, schedule.plan_id, user_id)
    schedule.plan = plan
    return schedule


@dataclass(frozen=True, slots=True)
class CreatePlanCommand:
    user_id: uuid.UUID
    name: str
    amount: Amount
    term: TermType
    interest_rate: InterestRate
    start_date: datetime.date
    early_payment_fees: EarlyPaymentFees | None = None
    interest_rate_application: InterestRateApplication = InterestRateApplication.WholeMonth


class CreatePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, command: CreatePlanCommand) -> Plan:
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        interest_rate = (
            command.interest_rate if isinstance(command.interest_rate, Decimal) else Decimal(command.interest_rate)
        )
        if isinstance(command.term, int):
            term = Term(command.term, 0)
        elif isinstance(command.term, tuple):
            term = Term(*command.term)
        else:
            term = command.term
        plan = Plan(
            user_id=command.user_id,
            name=command.name,
            slug=command.name.lower().replace(" ", "-"),
            amount=amount,
            term=term,
            interest_rate=interest_rate,
            start_date=command.start_date,
            early_payment_fees=command.early_payment_fees
            if command.early_payment_fees is not None
            else EarlyPaymentFees(),
            interest_rate_application=command.interest_rate_application,
        )
        await self._plan_repo.add(plan)
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
    early_payment_fees: EarlyPaymentFees | None = None
    interest_rate_application: InterestRateApplication | None = None


class UpdatePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, command: UpdatePlanCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        if command.name is not None:
            plan.name = command.name
        if command.amount is not None:
            plan.amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        if command.term is not None:
            if isinstance(command.term, int):
                plan.term = Term(command.term, 0)
            elif isinstance(command.term, tuple):
                plan.term = Term(*command.term)
            else:
                plan.term = command.term
        if command.interest_rate is not None:
            plan.interest_rate = (
                command.interest_rate if isinstance(command.interest_rate, Decimal) else Decimal(command.interest_rate)
            )
        if command.start_date is not None:
            plan.start_date = command.start_date
        if command.early_payment_fees is not None:
            plan.early_payment_fees = command.early_payment_fees
        if command.interest_rate_application is not None:
            plan.interest_rate_application = command.interest_rate_application
        plan.touch()
        await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class DeletePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class DeletePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, command: DeletePlanCommand) -> None:
        await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        await self._plan_repo.delete(Id(command.plan_id))


@dataclass(frozen=True, slots=True)
class SavePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class SavePlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, command: SavePlanCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        plan.status = Plan.Status.Saved
        plan.touch()
        await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class AddOneTimeExtraPaymentCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    date: datetime.date
    amount: Amount


class AddOneTimeExtraPaymentHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, command: AddOneTimeExtraPaymentCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        plan.one_time_extra_payments.append(OneTimeExtraPayment(date=command.date, amount=amount))
        plan.touch()
        await self._plan_repo.update(plan)
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
        self._plan_repo = plan_repo

    async def handle(self, command: AddRecurringExtraPaymentCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        amount = command.amount if isinstance(command.amount, Decimal) else Decimal(command.amount)
        plan.recurring_extra_payments.append(
            RecurringExtraPayment(start_date=command.start_date, amount=amount, count=command.count)
        )
        plan.touch()
        await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class AddInterestRateChangeCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    effective_date: datetime.date
    rate: InterestRate


class AddInterestRateChangeHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, command: AddInterestRateChangeCommand) -> Plan:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        rate = command.rate if isinstance(command.rate, Decimal) else Decimal(command.rate)
        plan.interest_rate_changes.append(
            InterestRateChange(effective_date=command.effective_date, yearly_interest_rate=rate)
        )
        plan.interest_rate_changes.sort(key=lambda c: c.effective_date)
        plan.touch()
        await self._plan_repo.update(plan)
        return plan


@dataclass(frozen=True, slots=True)
class SaveScheduleCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class SaveScheduleHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan], schedule_repo: AsyncRepository[Schedule]) -> None:
        self._plan_repo = plan_repo
        self._schedule_repo = schedule_repo

    async def handle(self, command: SaveScheduleCommand) -> Schedule:
        plan = await _get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        schedule = plan.generate()
        await self._schedule_repo.add(schedule)
        return schedule


@dataclass(frozen=True, slots=True)
class DeleteScheduleCommand:
    schedule_id: uuid.UUID
    user_id: uuid.UUID


class DeleteScheduleHandler:
    def __init__(self, schedule_repo: AsyncRepository[Schedule], plan_repo: AsyncRepository[Plan]) -> None:
        self._schedule_repo = schedule_repo
        self._plan_repo = plan_repo

    async def handle(self, command: DeleteScheduleCommand) -> None:
        await _get_owned_schedule(self._schedule_repo, self._plan_repo, command.schedule_id, command.user_id)
        await self._schedule_repo.delete(Id(command.schedule_id))
