"""Get a plan by ID with ownership verification."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class GetPlanQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class GetPlanHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, query: GetPlanQuery) -> Plan:
        return get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
