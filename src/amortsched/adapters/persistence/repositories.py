from collections.abc import Sequence
from typing import Any, Never, cast
from uuid import UUID

import sqlalchemy
from sqlalchemy.exc import IntegrityError

from amortsched.adapters.persistence.base import AsyncRepository as BaseAsyncRepository
from amortsched.adapters.persistence.helpers import build_postgres_upsert_statement
from amortsched.adapters.persistence.mappers import (
    plan_from_row,
    plan_to_values,
    profile_from_row,
    profile_to_values,
    refresh_token_from_row,
    refresh_token_to_values,
    schedule_from_row,
    schedule_to_values,
    user_from_row,
    user_to_values,
)
from amortsched.adapters.persistence.relationships import PlannedRelation, Relationship
from amortsched.adapters.persistence.specifications import compile_specification
from amortsched.adapters.persistence.tables import plans, profiles, refresh_tokens, schedules, users
from amortsched.core.entities import Plan, Profile, RefreshToken, Schedule, User
from amortsched.core.errors import (
    DuplicateEmailError,
    PlanNotFoundError,
    ProfileNotFoundError,
    RefreshTokenNotFoundError,
    ScheduleNotFoundError,
    UserNotFoundError,
)
from amortsched.core.specifications import Rel, Specification


class AsyncSqlAlchemyUserRepository(BaseAsyncRepository[User]):
    _table = users
    _from_row = staticmethod(user_from_row)
    _to_values = staticmethod(user_to_values)
    _not_found_error = UserNotFoundError
    _relationships = {
        "plans": Relationship(
            key="plans",
            table=plans,
            entity=Plan,
            root_key_column=users.c.id,
            related_key_column=plans.c.user_id,
            many=True,
        ),
        "profile": Relationship(
            key="profile",
            table=profiles,
            entity=Profile,
            root_key_column=users.c.id,
            related_key_column=profiles.c.user_id,
        ),
    }

    @staticmethod
    def _build_plans_statement(user_ids: list[UUID], relation: Rel[Any]):
        statement = sqlalchemy.select(plans).where(plans.c.user_id.in_(user_ids)).order_by(plans.c.created_at)
        if relation.spec is not None:
            statement = statement.where(compile_specification(plans, relation.spec))
        return statement

    @staticmethod
    def _build_profiles_statement(user_ids: list[UUID], relation: Rel[Any]):
        statement = sqlalchemy.select(profiles).where(profiles.c.user_id.in_(user_ids))
        if relation.spec is not None:
            statement = statement.where(compile_specification(profiles, relation.spec))
        return statement

    @staticmethod
    def _raise_duplicate_email(exc: IntegrityError, email: str) -> Never:
        message = str(exc.orig)
        if (
            "uq_users_email" in message
            or "users_email_key" in message
            or "UNIQUE constraint failed: users.email" in message
        ):
            raise DuplicateEmailError(email) from exc
        raise exc

    async def add(self, item: User) -> User:
        statement = sqlalchemy.insert(users).values(**user_to_values(item))
        try:
            await self._session.execute(statement)
        except IntegrityError as exc:
            self._raise_duplicate_email(exc, item.email)
        return item

    async def update(self, item: User) -> User:
        statement = sqlalchemy.update(users).where(users.c.id == item.id).values(**user_to_values(item))
        result = None
        try:
            result = await self._session.execute(statement)
        except IntegrityError as exc:
            self._raise_duplicate_email(exc, item.email)
        if result is None or result.rowcount == 0:
            raise UserNotFoundError(item.id)
        return item

    async def save(self, item: User, conflict_on: Sequence[str] = ("id",)) -> User:
        statement = build_postgres_upsert_statement(users, user_to_values(item), conflict_on)
        try:
            await self._session.execute(statement)
        except IntegrityError as exc:
            self._raise_duplicate_email(exc, item.email)
        return item

    async def _load_relations(self, items: list[User], relations: list[PlannedRelation]) -> None:
        if not items:
            return
        user_ids = [item.id for item in items]
        users_by_id = {item.id: item for item in items}

        for relation in relations:
            if relation.relationship.key == "plans":
                await self._load_plans(users_by_id, user_ids, relation.relation)
            elif relation.relationship.key == "profile":
                await self._load_profile(users_by_id, user_ids, relation.relation)

    async def _load_plans(self, users_by_id: dict[UUID, User], user_ids: list[UUID], relation: Rel[Any]) -> None:
        statement = self._build_plans_statement(user_ids, relation)
        rows = (await self._session.execute(statement)).mappings().all()

        plans_by_user: dict[UUID, list[Plan]] = {user_id: [] for user_id in user_ids}
        for row in rows:
            plan = plan_from_row(row)
            plan.user = users_by_id[plan.user_id]
            plans_by_user[plan.user_id].append(plan)

        for user_id, user in users_by_id.items():
            user.plans = plans_by_user.get(user_id, [])

    async def _load_profile(self, users_by_id: dict[UUID, User], user_ids: list[UUID], relation: Rel[Any]) -> None:
        statement = self._build_profiles_statement(user_ids, relation)
        rows = (await self._session.execute(statement)).mappings().all()

        profiles_by_user = {cast(UUID, row["user_id"]): profile_from_row(row) for row in rows}
        for profile in profiles_by_user.values():
            profile.user = users_by_id[profile.user_id]
        for user_id, user in users_by_id.items():
            user.profile = profiles_by_user.get(user_id)


class AsyncSqlAlchemyPlanRepository(BaseAsyncRepository[Plan]):
    _table = plans
    _from_row = staticmethod(plan_from_row)
    _to_values = staticmethod(plan_to_values)
    _not_found_error = PlanNotFoundError
    _relationships = {
        "user": Relationship(
            key="user",
            table=users,
            entity=User,
            root_key_column=plans.c.user_id,
            related_key_column=users.c.id,
        ),
        "schedules": Relationship(
            key="schedules",
            table=schedules,
            entity=Schedule,
            root_key_column=plans.c.id,
            related_key_column=schedules.c.plan_id,
            many=True,
        ),
    }

    @staticmethod
    def _build_users_statement(user_ids: list[UUID], specification: Specification[User] | None = None):
        statement = sqlalchemy.select(users).where(users.c.id.in_(user_ids))
        if specification is not None:
            statement = statement.where(compile_specification(users, specification))
        return statement

    @staticmethod
    def _build_schedules_statement(plan_ids: list[UUID], relation: Rel[Any]):
        statement = (
            sqlalchemy.select(schedules).where(schedules.c.plan_id.in_(plan_ids)).order_by(schedules.c.generated_at)
        )
        if relation.spec is not None:
            statement = statement.where(compile_specification(schedules, relation.spec))
        return statement

    async def _load_relations(self, items: list[Plan], relations: list[PlannedRelation]) -> None:
        if not items:
            return
        plan_ids = [item.id for item in items]
        plans_by_id = {item.id: item for item in items}

        for relation in relations:
            if relation.relationship.key == "user":
                await self._load_users(plans_by_id, relation.relation)
            elif relation.relationship.key == "schedules":
                await self._load_schedules(plans_by_id, plan_ids, relation.relation)

    async def _load_users(self, plans_by_id: dict[UUID, Plan], relation: Rel[Any]) -> None:
        user_ids = [plan.user_id for plan in plans_by_id.values()]
        statement = self._build_users_statement(user_ids, relation.spec)
        rows = (await self._session.execute(statement)).mappings().all()

        users_by_id = {cast(UUID, row["id"]): user_from_row(row) for row in rows}
        for plan in plans_by_id.values():
            plan.user = users_by_id.get(plan.user_id)

    async def _load_schedules(
        self,
        plans_by_id: dict[UUID, Plan],
        plan_ids: list[UUID],
        relation: Rel[Any],
    ) -> None:
        statement = self._build_schedules_statement(plan_ids, relation)
        rows = (await self._session.execute(statement)).mappings().all()

        schedules_by_plan: dict[UUID, list[Schedule]] = {plan_id: [] for plan_id in plan_ids}
        for row in rows:
            schedule = schedule_from_row(row)
            schedule.plan = plans_by_id[schedule.plan_id]
            schedules_by_plan[schedule.plan_id].append(schedule)

        for plan_id, plan in plans_by_id.items():
            plan.schedules = schedules_by_plan.get(plan_id, [])


class AsyncSqlAlchemyScheduleRepository(BaseAsyncRepository[Schedule]):
    _table = schedules
    _from_row = staticmethod(schedule_from_row)
    _to_values = staticmethod(schedule_to_values)
    _order_column = "generated_at"
    _not_found_error = ScheduleNotFoundError
    _relationships = {
        "plan": Relationship(
            key="plan",
            table=plans,
            entity=Plan,
            root_key_column=schedules.c.plan_id,
            related_key_column=plans.c.id,
        )
    }

    @staticmethod
    def _build_plans_statement(plan_ids: list[UUID], specification: Specification[Plan] | None = None):
        statement = sqlalchemy.select(plans).where(plans.c.id.in_(plan_ids))
        if specification is not None:
            statement = statement.where(compile_specification(plans, specification))
        return statement

    async def _load_relations(self, items: list[Schedule], relations: list[PlannedRelation]) -> None:
        if not items:
            return
        schedules_by_id = {item.id: item for item in items}
        plan_ids = [item.plan_id for item in items]

        for relation in relations:
            if relation.relationship.key != "plan":
                continue
            statement = self._build_plans_statement(plan_ids, relation.relation.spec)
            rows = (await self._session.execute(statement)).mappings().all()
            plans_by_id = {cast(UUID, row["id"]): plan_from_row(row) for row in rows}
            for schedule in schedules_by_id.values():
                schedule.plan = plans_by_id.get(schedule.plan_id)


class AsyncSqlAlchemyProfileRepository(BaseAsyncRepository[Profile]):
    _table = profiles
    _from_row = staticmethod(profile_from_row)
    _to_values = staticmethod(profile_to_values)
    _not_found_error = ProfileNotFoundError
    _relationships = {
        "user": Relationship(
            key="user",
            table=users,
            entity=User,
            root_key_column=profiles.c.user_id,
            related_key_column=users.c.id,
        )
    }

    @staticmethod
    def _build_users_statement(profile_user_ids: list[UUID], specification: Specification[User] | None = None):
        statement = sqlalchemy.select(users).where(users.c.id.in_(profile_user_ids))
        if specification is not None:
            statement = statement.where(compile_specification(users, specification))
        return statement

    async def _load_relations(self, items: list[Profile], relations: list[PlannedRelation]) -> None:
        if not items:
            return
        profile_user_ids = [item.user_id for item in items]
        profiles_by_user_id = {item.user_id: item for item in items}

        for relation in relations:
            if relation.relationship.key != "user":
                continue
            statement = self._build_users_statement(profile_user_ids, relation.relation.spec)
            rows = (await self._session.execute(statement)).mappings().all()
            for row in rows:
                user = user_from_row(row)
                profiles_by_user_id[user.id].user = user


class AsyncSqlAlchemyRefreshTokenRepository(BaseAsyncRepository[RefreshToken]):
    _table = refresh_tokens
    _from_row = staticmethod(refresh_token_from_row)
    _to_values = staticmethod(refresh_token_to_values)
    _not_found_error = RefreshTokenNotFoundError
    _relationships: dict[str, Relationship] = {}

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        statement = sqlalchemy.select(refresh_tokens).where(refresh_tokens.c.token_hash == token_hash)
        row = (await self._session.execute(statement)).mappings().first()
        if row is None:
            return None
        return refresh_token_from_row(row)

    async def revoke_family(self, family_id: UUID) -> int:
        statement = (
            sqlalchemy.update(refresh_tokens)
            .where(refresh_tokens.c.family_id == family_id)
            .where(refresh_tokens.c.revoked_at.is_(None))
            .values(revoked_at=sqlalchemy.func.now())
        )
        result = await self._session.execute(statement)
        return result.rowcount

    async def mark_used(self, token_id: UUID) -> None:
        statement = (
            sqlalchemy.update(refresh_tokens)
            .where(refresh_tokens.c.id == token_id)
            .values(used_at=sqlalchemy.func.now())
        )
        await self._session.execute(statement)
