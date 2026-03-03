"""Transition a plan from Draft to Saved status."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class SavePlanCommand:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class SavePlanHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, command: SavePlanCommand) -> Plan:
        plan = get_owned_plan(self._plan_repo, command.plan_id, command.user_id)
        plan.status = Plan.Status.Saved
        plan.touch()
        self._plan_repo.update(plan)
        return plan
