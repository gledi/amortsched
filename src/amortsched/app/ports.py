import uuid
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self

from amortsched.core.entities import Plan, Profile, Schedule, User
from amortsched.core.repositories import AccountTokenRepository, AsyncRepository, RefreshTokenRepository


class SecuritySettings(Protocol):
    @property
    def secret_key(self) -> str: ...
    @property
    def token_expiration_minutes(self) -> int: ...
    @property
    def refresh_token_expiration_days(self) -> int: ...


class DatabaseSettings(Protocol):
    @property
    def url(self) -> str: ...


class Settings(Protocol):
    @property
    def public_url(self) -> str: ...
    @property
    def security(self) -> SecuritySettings: ...
    @property
    def database(self) -> DatabaseSettings: ...
    @property
    def debug(self) -> bool: ...


class TokenService(Protocol):
    def create_access_token(self, user_id: uuid.UUID) -> str: ...
    def decode_access_token(self, token: str) -> uuid.UUID: ...
    def create_refresh_token(self) -> str: ...
    def hash_refresh_token(self, token: str) -> str: ...


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str | None = None


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        """Record one attempt; return seconds until retry when over the limit, else None."""
        ...


class AsyncUnitOfWork(Protocol):
    users: AsyncRepository[User]
    profiles: AsyncRepository[Profile]
    plans: AsyncRepository[Plan]
    schedules: AsyncRepository[Schedule]
    refresh_tokens: RefreshTokenRepository
    account_tokens: AccountTokenRepository

    async def begin(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None: ...
