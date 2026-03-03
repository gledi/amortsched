"""Delete a saved schedule."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan, Schedule
from amortsched.core.repositories import Repository
from amortsched.core.specifications import Id

from ._helpers import get_owned_schedule


@dataclass(frozen=True, slots=True)
class DeleteScheduleCommand:
    schedule_id: uuid.UUID
    user_id: uuid.UUID


class DeleteScheduleHandler:
    def __init__(self, schedule_repo: Repository[Schedule], plan_repo: Repository[Plan]) -> None:
        self._schedule_repo = schedule_repo
        self._plan_repo = plan_repo

    def handle(self, command: DeleteScheduleCommand) -> None:
        get_owned_schedule(self._schedule_repo, self._plan_repo, command.schedule_id, command.user_id)
        self._schedule_repo.delete(Id(command.schedule_id))
