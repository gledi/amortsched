"""Get a user by ID."""

import uuid
from dataclasses import dataclass

from amortsched.core.entities import User
from amortsched.core.errors import UserNotFoundError
from amortsched.core.repositories import Repository


@dataclass(frozen=True, slots=True)
class GetUserQuery:
    user_id: uuid.UUID


class GetUserHandler:
    def __init__(self, user_repo: Repository[User]) -> None:
        self._user_repo = user_repo

    def handle(self, query: GetUserQuery) -> User:
        user = self._user_repo.get_by_id(query.user_id)
        if user is None:
            raise UserNotFoundError(query.user_id)
        return user
