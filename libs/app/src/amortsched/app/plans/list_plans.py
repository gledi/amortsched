"""List plans for a user."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan
from amortsched.core.repositories import Repository
from amortsched.core.specifications import Eq


@dataclass(frozen=True, slots=True)
class ListPlansQuery:
    user_id: uuid.UUID


class ListPlansHandler:
    def __init__(self, plan_repo: Repository[Plan]) -> None:
        self._plan_repo = plan_repo

    def handle(self, query: ListPlansQuery) -> list[Plan]:
        return list(self._plan_repo.get_items(Eq("user_id", query.user_id)))
