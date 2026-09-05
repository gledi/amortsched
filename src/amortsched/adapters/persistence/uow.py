from typing import Any, Callable, Self, override

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
        self._session_factory = session_factory  # pyright: ignore[reportUnannotatedClassAttribute]
        self._session: AsyncSession | None = None
        self._committed = False  # pyright: ignore[reportUnannotatedClassAttribute]

    @override
    async def begin(self) -> None:
        self._session = self._session_factory()
        self._committed = False
        self.users = AsyncSqlAlchemyUserRepository(self._session)  # pyright: ignore[reportUnannotatedClassAttribute]
        self.profiles = AsyncSqlAlchemyProfileRepository(self._session)  # pyright: ignore[reportUnannotatedClassAttribute]
        self.plans = AsyncSqlAlchemyPlanRepository(self._session)  # pyright: ignore[reportUnannotatedClassAttribute]
        self.schedules = AsyncSqlAlchemyScheduleRepository(self._session)  # pyright: ignore[reportUnannotatedClassAttribute]

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
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:  # pyright: ignore[reportAny, reportExplicitAny]
        if exc_type is not None:
            await self.rollback()
        elif not self._committed:
            await self.rollback()
        await self.close()
