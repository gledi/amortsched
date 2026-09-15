import uuid
from dataclasses import dataclass

from amortsched.app.access import get_owned_plan, get_owned_schedule
from amortsched.core.entities import Plan, Schedule
from amortsched.core.repositories import AsyncRepository
from amortsched.core.specifications import Eq

_get_owned_plan = get_owned_plan
_get_owned_schedule = get_owned_schedule


@dataclass(frozen=True, slots=True)
class GenerateScheduleQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class GenerateScheduleHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan], schedule_repo: AsyncRepository[Schedule]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo
        self._schedule_repo: AsyncRepository[Schedule] = schedule_repo

    async def handle(self, query: GenerateScheduleQuery) -> Schedule:
        plan = await _get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
        schedule = plan.generate()
        return await self._schedule_repo.add(schedule)


@dataclass(frozen=True, slots=True)
class GetScheduleQuery:
    schedule_id: uuid.UUID
    plan_id: uuid.UUID
    user_id: uuid.UUID


class GetScheduleHandler:
    def __init__(self, schedule_repo: AsyncRepository[Schedule], plan_repo: AsyncRepository[Plan]) -> None:
        self._schedule_repo: AsyncRepository[Schedule] = schedule_repo
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, query: GetScheduleQuery) -> Schedule:
        return await _get_owned_schedule(
            self._schedule_repo, self._plan_repo, query.schedule_id, query.plan_id, query.user_id
        )


@dataclass(frozen=True, slots=True)
class ListSchedulesQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID
    limit: int | None = None


class ListSchedulesHandler:
    def __init__(self, schedule_repo: AsyncRepository[Schedule], plan_repo: AsyncRepository[Plan]) -> None:
        self._schedule_repo: AsyncRepository[Schedule] = schedule_repo
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, query: ListSchedulesQuery) -> list[Schedule]:
        _ = await _get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
        return [
            item
            async for item in self._schedule_repo.get_items(
                Eq("plan_id", query.plan_id),
                limit=query.limit,
            )
        ]
