from collections.abc import Callable
from types import TracebackType
from typing import Self, override

from sqlalchemy.ext.asyncio import AsyncSession

from amortsched.adapters.persistence.repositories import (
    AsyncSqlAlchemyPlanRepository,
    AsyncSqlAlchemyProfileRepository,
    AsyncSqlAlchemyRefreshTokenRepository,
    AsyncSqlAlchemyScheduleRepository,
    AsyncSqlAlchemyUserRepository,
)
from amortsched.app.ports import AsyncUnitOfWork


class AsyncSqlAlchemyUnitOfWork(AsyncUnitOfWork):
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory: Callable[[], AsyncSession] = session_factory
        self._session: AsyncSession | None = None
        self._committed: bool = False

    @override
    async def begin(self) -> None:
        self._session = self._session_factory()
        self._committed = False
        self.users = AsyncSqlAlchemyUserRepository(self._session)
        self.profiles = AsyncSqlAlchemyProfileRepository(self._session)
        self.plans = AsyncSqlAlchemyPlanRepository(self._session)
        self.schedules = AsyncSqlAlchemyScheduleRepository(self._session)
        self.refresh_tokens = AsyncSqlAlchemyRefreshTokenRepository(self._session)

    @override
    async def commit(self) -> None:
        if not self._session:
            raise RuntimeError("Cannot commit before begin")
        if self._committed:
            raise RuntimeError("Already committed")
        await self._session.commit()
        self._committed = True

    @override
    async def rollback(self) -> None:
        if self._session and not self._committed:
            await self._session.rollback()

    @override
    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    @override
    async def __aenter__(self) -> Self:
        await self.begin()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        if exc_type is not None or not self._committed:
            await self.rollback()
        await self.close()
        return None
