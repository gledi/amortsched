import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan, Schedule
from amortsched.core.errors import PlanNotFoundError, PlanOwnershipError, ScheduleNotFoundError
from amortsched.core.repositories import AsyncRepository
from amortsched.core.specifications import Eq


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
class GenerateScheduleQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class GenerateScheduleHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, query: GenerateScheduleQuery) -> Schedule:
        plan = await _get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
        return plan.generate()


@dataclass(frozen=True, slots=True)
class GetScheduleQuery:
    schedule_id: uuid.UUID
    user_id: uuid.UUID


class GetScheduleHandler:
    def __init__(self, schedule_repo: AsyncRepository[Schedule], plan_repo: AsyncRepository[Plan]) -> None:
        self._schedule_repo = schedule_repo
        self._plan_repo = plan_repo

    async def handle(self, query: GetScheduleQuery) -> Schedule:
        return await _get_owned_schedule(self._schedule_repo, self._plan_repo, query.schedule_id, query.user_id)


@dataclass(frozen=True, slots=True)
class ListSchedulesQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class ListSchedulesHandler:
    def __init__(self, schedule_repo: AsyncRepository[Schedule], plan_repo: AsyncRepository[Plan]) -> None:
        self._schedule_repo = schedule_repo
        self._plan_repo = plan_repo

    async def handle(self, query: ListSchedulesQuery) -> list[Schedule]:
        await _get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
        return [item async for item in self._schedule_repo.get_items(Eq("plan_id", query.plan_id))]
