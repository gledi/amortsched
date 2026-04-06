from typing import Any, Callable, Self

from sqlalchemy.ext.asyncio import AsyncSession

from amortsched.adapters.persistence.repositories import (
    AsyncSqlAlchemyPlanRepository,
    AsyncSqlAlchemyProfileRepository,
    AsyncSqlAlchemyScheduleRepository,
    AsyncSqlAlchemyUserRepository,
)
from amortsched.app.ports import AsyncUnitOfWork


class AsyncSqlAlchemyUnitOfWork(AsyncUnitOfWork):
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def begin(self) -> None:
        self._session = self._session_factory()
        self._committed = False
        self.users = AsyncSqlAlchemyUserRepository(self._session)
        self.profiles = AsyncSqlAlchemyProfileRepository(self._session)
        self.plans = AsyncSqlAlchemyPlanRepository(self._session)
        self.schedules = AsyncSqlAlchemyScheduleRepository(self._session)

    async def commit(self) -> None:
        if not self._session:
            raise RuntimeError("Cannot commit before begin")
        if self._committed:
            raise RuntimeError("Already committed")
        await self._session.commit()
        self._committed = True

    async def rollback(self) -> None:
        if self._session and not self._committed:
            await self._session.rollback()

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> Self:
        await self.begin()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        elif not self._committed:
            await self.rollback()
        await self.close()
