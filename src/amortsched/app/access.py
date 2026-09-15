import uuid

from amortsched.core.entities import Plan, Schedule
from amortsched.core.errors import PlanNotFoundError, PlanOwnershipError, ScheduleNotFoundError
from amortsched.core.repositories import AsyncRepository


async def get_owned_plan(plan_repo: AsyncRepository[Plan], plan_id: uuid.UUID, user_id: uuid.UUID) -> Plan:
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


async def get_owned_schedule(
    schedule_repo: AsyncRepository[Schedule],
    plan_repo: AsyncRepository[Plan],
    schedule_id: uuid.UUID,
    plan_id: uuid.UUID,
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
    if schedule.plan_id != plan_id:
        raise ScheduleNotFoundError(schedule_id)
    plan = await get_owned_plan(plan_repo, schedule.plan_id, user_id)
    schedule.plan = plan
    return schedule
