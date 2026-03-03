"""Register a new user."""

from dataclasses import dataclass

from amortsched.core.entities import User
from amortsched.core.repositories import Repository
from amortsched.core.security import PasswordHasher


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    name: str
    password: str


class RegisterUserHandler:
    def __init__(self, user_repo: Repository[User], password_hasher: PasswordHasher) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    def handle(self, command: RegisterUserCommand) -> User:
        password_hash = self._password_hasher.hash(command.password)
        user = User(email=command.email, name=command.name, password_hash=password_hash)
        self._user_repo.add(user)
        return user
