import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan
from amortsched.core.errors import PlanNotFoundError, PlanOwnershipError
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


@dataclass(frozen=True, slots=True)
class GetPlanQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class GetPlanHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, query: GetPlanQuery) -> Plan:
        return await _get_owned_plan(self._plan_repo, query.plan_id, query.user_id)


@dataclass(frozen=True, slots=True)
class ListPlansQuery:
    user_id: uuid.UUID


class ListPlansHandler:
    def __init__(self, plan_repo: AsyncRepository[Plan]) -> None:
        self._plan_repo = plan_repo

    async def handle(self, query: ListPlansQuery) -> list[Plan]:
        return [item async for item in self._plan_repo.get_items(Eq("user_id", query.user_id))]
