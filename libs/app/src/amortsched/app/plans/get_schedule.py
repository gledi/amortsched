"""Get a saved schedule by ID."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan, Schedule
from amortsched.core.repositories import Repository

from ._helpers import get_owned_schedule


@dataclass(frozen=True, slots=True)
class GetScheduleQuery:
    schedule_id: uuid.UUID
    user_id: uuid.UUID


class GetScheduleHandler:
    def __init__(self, schedule_repo: Repository[Schedule], plan_repo: Repository[Plan]) -> None:
        self._schedule_repo = schedule_repo
        self._plan_repo = plan_repo

    def handle(self, query: GetScheduleQuery) -> Schedule:
        return get_owned_schedule(self._schedule_repo, self._plan_repo, query.schedule_id, query.user_id)
