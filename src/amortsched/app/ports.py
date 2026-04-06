import uuid
from types import TracebackType
from typing import Protocol, Self

from amortsched.core.entities import Plan, Profile, Schedule, User
from amortsched.core.repositories import AsyncRepository


class TokenService(Protocol):
    def create_access_token(self, user_id: uuid.UUID) -> str: ...
    def decode_access_token(self, token: str) -> uuid.UUID: ...


class AsyncUnitOfWork(Protocol):
    users: AsyncRepository[User]
    profiles: AsyncRepository[Profile]
    plans: AsyncRepository[Plan]
    schedules: AsyncRepository[Schedule]

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
