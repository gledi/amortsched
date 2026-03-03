"""List saved schedules for a plan."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan, Schedule
from amortsched.core.repositories import Repository
from amortsched.core.specifications import Eq

from ._helpers import get_owned_plan


@dataclass(frozen=True, slots=True)
class ListSchedulesQuery:
    plan_id: uuid.UUID
    user_id: uuid.UUID


class ListSchedulesHandler:
    def __init__(self, schedule_repo: Repository[Schedule], plan_repo: Repository[Plan]) -> None:
        self._schedule_repo = schedule_repo
        self._plan_repo = plan_repo

    def handle(self, query: ListSchedulesQuery) -> list[Schedule]:
        get_owned_plan(self._plan_repo, query.plan_id, query.user_id)
        return list(self._schedule_repo.get_items(Eq("plan_id", query.plan_id)))
