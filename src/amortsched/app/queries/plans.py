import uuid
from dataclasses import dataclass

from amortsched.app.access import get_owned_plan
from amortsched.core.entities import Plan
from amortsched.core.repositories import AsyncRepository
from amortsched.core.specifications import Eq

_get_owned_plan = get_owned_plan


@dataclass(frozen=True, slots=True)
class GetPlanQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class GetPlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, query: GetPlanQuery) -> Plan:
        return await _get_owned_plan(self._plan_repo, query.plan_id, query.user_id)


@dataclass(frozen=True, slots=True)
class ListPlansQuery:
    user_id: uuid.UUID
    limit: int | None = None


class ListPlansHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, query: ListPlansQuery) -> list[Plan]:
        return [
            item
            async for item in self._plan_repo.get_items(
                Eq("user_id", query.user_id),
                limit=query.limit,
            )
        ]
