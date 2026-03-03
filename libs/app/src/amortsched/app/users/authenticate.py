"""Authenticate a user by email and password."""

from dataclasses import dataclass

from amortsched.core.entities import User
from amortsched.core.errors import AuthenticationError
from amortsched.core.repositories import Repository
from amortsched.core.security import PasswordHasher
from amortsched.core.specifications import Eq


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    email: str
    password: str


class AuthenticateUserHandler:
    def __init__(self, user_repo: Repository[User], password_hasher: PasswordHasher) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    def handle(self, command: AuthenticateUserCommand) -> User:
        user = self._user_repo.get_one_or_none(Eq("email", command.email))
        if user is None:
            raise AuthenticationError()
        if not self._password_hasher.verify(command.password, user.password_hash):
            raise AuthenticationError()
        return user
