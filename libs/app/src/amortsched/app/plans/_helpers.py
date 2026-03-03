"""Shared helpers for plan use case handlers."""

import uuid

from amortsched.core.entities import Plan, Schedule
from amortsched.core.errors import PlanNotFoundError, PlanOwnershipError, ScheduleNotFoundError
from amortsched.core.repositories import Repository


def get_owned_plan(plan_repo: Repository[Plan], plan_id: uuid.UUID, user_id: uuid.UUID) -> Plan:
    """Fetch a plan and verify ownership.

    Raises:
        PlanNotFoundError: If the plan does not exist.
        PlanOwnershipError: If the plan belongs to a different user.
    """
    plan = plan_repo.get_by_id(plan_id)
    if plan is None:
        raise PlanNotFoundError(plan_id)
    if plan.user_id != user_id:
        raise PlanOwnershipError(plan_id, user_id)
    return plan


def get_owned_schedule(
    schedule_repo: Repository[Schedule],
    plan_repo: Repository[Plan],
    schedule_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Schedule:
    """Fetch a schedule and verify ownership transitively through its plan.

    Raises:
        ScheduleNotFoundError: If the schedule does not exist.
        PlanNotFoundError: If the associated plan does not exist.
        PlanOwnershipError: If the plan belongs to a different user.
    """
    schedule = schedule_repo.get_by_id(schedule_id)
    if schedule is None:
        raise ScheduleNotFoundError(schedule_id)
    get_owned_plan(plan_repo, schedule.plan_id, user_id)
    return schedule
