"""Save a generated schedule for a plan."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan, Schedule
from amortsched.core.repositories import Repository

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class SaveScheduleCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class SaveScheduleHandler:
    def __init__(self, plan_repo: Repository[Plan], schedule_repo: Repository[Schedule]) -> None:
        self._plan_repo = plan_repo
        self._schedule_repo = schedule_repo

    def handle(self, command: SaveScheduleCommand) -> Schedule:
        plan = get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        schedule = plan.generate()
        self._schedule_repo.add(schedule)
        return schedule
