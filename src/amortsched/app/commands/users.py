import asyncio
import datetime
import uuid
from dataclasses import dataclass

from amortsched.app.ports import Settings, TokenService
from amortsched.core.entities import Profile, RefreshToken, User
from amortsched.core.errors import (
    AuthenticationError,
    RefreshTokenNotFoundError,
    RefreshTokenReplayError,
    UserNotFoundError,
)
from amortsched.core.repositories import AsyncRepository, RefreshTokenRepository
from amortsched.core.security import PasswordHasher
from amortsched.core.specifications import Eq
from amortsched.core.utils import now


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


@dataclass(frozen=True, slots=True)
class RefreshTokensCommand:
    refresh_token: str


@dataclass
class RefreshTokensResult:
    access_token: str
    refresh_token: str


class RefreshTokensHandler:
    def __init__(
        self,
        refresh_token_repo: RefreshTokenRepository,
        token_service: TokenService,
        settings: Settings,
    ) -> None:
        self._refresh_token_repo = refresh_token_repo
        self._token_service = token_service
        self._settings = settings

    async def handle(self, command: RefreshTokensCommand) -> RefreshTokensResult:
        token_hash = self._token_service.hash_refresh_token(command.refresh_token)
        existing = await self._refresh_token_repo.get_by_token_hash(token_hash)

        if existing is None or existing.expires_at < now() or existing.revoked_at is not None:
            raise RefreshTokenNotFoundError()

        if existing.used_at is not None:
            await self._refresh_token_repo.revoke_family(existing.family_id)
            raise RefreshTokenReplayError()

        await self._refresh_token_repo.mark_used(existing.id)

        raw_token = self._token_service.create_refresh_token()
        new_token = RefreshToken(
            user_id=existing.user_id,
            token_hash=self._token_service.hash_refresh_token(raw_token),
            family_id=existing.family_id,
            expires_at=now() + datetime.timedelta(days=self._settings.refresh_token_expiration_days),
        )
        await self._refresh_token_repo.add(new_token)

        access_token = self._token_service.create_access_token(existing.user_id)
        return RefreshTokensResult(access_token=access_token, refresh_token=raw_token)


@dataclass(frozen=True, slots=True)
class LogoutCommand:
    refresh_token: str


class LogoutHandler:
    def __init__(
        self,
        refresh_token_repo: RefreshTokenRepository,
        token_service: TokenService,
    ) -> None:
        self._refresh_token_repo = refresh_token_repo
        self._token_service = token_service

    async def handle(self, command: LogoutCommand) -> None:
        token_hash = self._token_service.hash_refresh_token(command.refresh_token)
        existing = await self._refresh_token_repo.get_by_token_hash(token_hash)
        if existing is not None:
            await self._refresh_token_repo.revoke_family(existing.family_id)


@dataclass(frozen=True, slots=True)
class CreateRefreshTokenCommand:
    user_id: uuid.UUID


class CreateRefreshTokenHandler:
    def __init__(
        self,
        refresh_token_repo: RefreshTokenRepository,
        token_service: TokenService,
        settings: Settings,
    ) -> None:
        self._refresh_token_repo = refresh_token_repo
        self._token_service = token_service
        self._settings = settings

    async def handle(self, command: CreateRefreshTokenCommand) -> str:
        raw_token = self._token_service.create_refresh_token()
        token = RefreshToken(
            user_id=command.user_id,
            token_hash=self._token_service.hash_refresh_token(raw_token),
            family_id=uuid.uuid4(),
            expires_at=now() + datetime.timedelta(days=self._settings.refresh_token_expiration_days),
        )
        await self._refresh_token_repo.add(token)
        return raw_token
