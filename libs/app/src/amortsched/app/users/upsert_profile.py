"""Create or update a user profile."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import Profile, User
from amortsched.core.errors import UserNotFoundError
from amortsched.core.repositories import Repository
from amortsched.core.specifications import Eq


@dataclass(frozen=True, slots=True)
class UpsertProfileCommand:
    user_id: uuid.UUID
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None


class UpsertProfileHandler:
    def __init__(self, profile_repo: Repository[Profile], user_repo: Repository[User]) -> None:
        self._profile_repo = profile_repo
        self._user_repo = user_repo

    def handle(self, command: UpsertProfileCommand) -> Profile:
        user = self._user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundError(command.user_id)

        existing = self._profile_repo.get_one_or_none(Eq("user_id", command.user_id))
        if existing is not None:
            existing.display_name = command.display_name
            existing.phone = command.phone
            existing.locale = command.locale
            existing.timezone = command.timezone
            existing.touch()
            self._profile_repo.update(existing)
            return existing

        profile = Profile(
            user_id=command.user_id,
            display_name=command.display_name,
            phone=command.phone,
            locale=command.locale,
            timezone=command.timezone,
        )
        self._profile_repo.add(profile)
        return profile
