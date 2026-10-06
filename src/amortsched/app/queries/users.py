import uuid
from dataclasses import dataclass

from amortsched.core.entities import Plan, Profile, User
from amortsched.core.errors import ProfileNotFoundError, UserNotFoundError
from amortsched.core.repositories import AsyncRepository
from amortsched.core.specifications import Eq


@dataclass(frozen=True, slots=True)
class GetUserQuery:
    user_id: uuid.UUID


class GetUserHandler:
    def __init__(self, user_repo: AsyncRepository[User]) -> None:
        self._user_repo: AsyncRepository[User] = user_repo

    async def handle(self, query: GetUserQuery) -> User:
        user = await self._user_repo.get_by_id(query.user_id)
        if user is None:
            raise UserNotFoundError(query.user_id)
        return user


@dataclass(frozen=True, slots=True)
class GetProfileQuery:
    user_id: uuid.UUID


class GetProfileHandler:
    def __init__(self, profile_repo: AsyncRepository[Profile]) -> None:
        self._profile_repo: AsyncRepository[Profile] = profile_repo

    async def handle(self, query: GetProfileQuery) -> Profile:
        profile = await self._profile_repo.get_one_or_none(Eq("user_id", query.user_id))
        if profile is None:
            raise ProfileNotFoundError(query.user_id)
        return profile


@dataclass(frozen=True, slots=True)
class ExportAccountDataQuery:
    user_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class AccountExport:
    user: User
    profile: Profile | None
    plans: list[Plan]


class ExportAccountDataHandler:
    def __init__(
        self,
        user_repo: AsyncRepository[User],
        profile_repo: AsyncRepository[Profile],
        plan_repo: AsyncRepository[Plan],
    ) -> None:
        self._user_repo: AsyncRepository[User] = user_repo
        self._profile_repo: AsyncRepository[Profile] = profile_repo
        self._plan_repo: AsyncRepository[Plan] = plan_repo

    async def handle(self, query: ExportAccountDataQuery) -> AccountExport:
        user = await self._user_repo.get_by_id(query.user_id)
        if user is None:
            raise UserNotFoundError(query.user_id)
        profile = await self._profile_repo.get_one_or_none(Eq("user_id", query.user_id))
        plans = [plan async for plan in self._plan_repo.get_items(Eq("user_id", query.user_id))]
        return AccountExport(user=user, profile=profile, plans=plans)
