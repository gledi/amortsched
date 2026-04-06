import asyncio
import uuid
from dataclasses import dataclass

from amortsched.core.entities import Profile, User
from amortsched.core.errors import AuthenticationError, UserNotFoundError
from amortsched.core.repositories import AsyncRepository
from amortsched.core.security import PasswordHasher
from amortsched.core.specifications import Eq


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    name: str
    password: str


class RegisterUserHandler:
    def __init__(self, user_repo: AsyncRepository[User], password_hasher: PasswordHasher) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def handle(self, command: RegisterUserCommand) -> User:
        password_hash = await asyncio.to_thread(self._password_hasher.hash, command.password)
        user = User(email=command.email, name=command.name, password_hash=password_hash)
        await self._user_repo.add(user)
        return user


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    email: str
    password: str


class AuthenticateUserHandler:
    def __init__(self, user_repo: AsyncRepository[User], password_hasher: PasswordHasher) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def handle(self, command: AuthenticateUserCommand) -> User:
        user = await self._user_repo.get_one_or_none(Eq("email", command.email))
        if user is None:
            raise AuthenticationError()
        if not await asyncio.to_thread(self._password_hasher.verify, command.password, user.password_hash):
            raise AuthenticationError()
        return user


@dataclass(frozen=True, slots=True)
class UpsertProfileCommand:
    user_id: uuid.UUID
    display_name: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None


class UpsertProfileHandler:
    def __init__(self, profile_repo: AsyncRepository[Profile], user_repo: AsyncRepository[User]) -> None:
        self._profile_repo = profile_repo
        self._user_repo = user_repo

    async def handle(self, command: UpsertProfileCommand) -> Profile:
        user = await self._user_repo.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundError(command.user_id)

        existing = await self._profile_repo.get_one_or_none(Eq("user_id", command.user_id))
        if existing is not None:
            existing.display_name = command.display_name
            existing.phone = command.phone
            existing.locale = command.locale
            existing.timezone = command.timezone
            existing.touch()
            await self._profile_repo.update(existing)
            return existing

        profile = Profile(
            user_id=command.user_id,
            display_name=command.display_name,
            phone=command.phone,
            locale=command.locale,
            timezone=command.timezone,
        )
        await self._profile_repo.add(profile)
        return profile
