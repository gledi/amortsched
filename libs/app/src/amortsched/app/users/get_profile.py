"""Get a user profile."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Profile
from amortsched.core.errors import ProfileNotFoundError
from amortsched.core.repositories import Repository
from amortsched.core.specifications import Eq


@dataclass(frozen=True, slots=True)
class GetProfileQuery:
    user_id: uuid.UUID


class GetProfileHandler:
    def __init__(self, profile_repo: Repository[Profile]) -> None:
        self._profile_repo = profile_repo

    def handle(self, query: GetProfileQuery) -> Profile:
        profile = self._profile_repo.get_one_or_none(Eq("user_id", query.user_id))
        if profile is None:
            raise ProfileNotFoundError(query.user_id)
        return profile
