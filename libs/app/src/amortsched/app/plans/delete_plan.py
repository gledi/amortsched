"""Delete a plan."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository
from amortsched.core.specifications import Id

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class DeletePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class DeletePlanHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, command: DeletePlanCommand) -> None:
        get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        self._plan_repo.delete(Id(command.plan_id))
