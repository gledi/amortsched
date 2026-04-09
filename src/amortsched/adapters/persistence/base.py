from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any, ClassVar, assert_type, cast
from uuid import UUID

import sqlalchemy
import sqlalchemy.ext.asyncio
import sqlalchemy.orm
from sqlalchemy.sql.schema import Table

from amortsched.adapters.persistence.helpers import (
    build_postgres_upsert_statement,
    build_single_statement_paginated_query,
    extract_paginated_items_and_total,
    normalize_paginated_limit,
)
from amortsched.adapters.persistence.mappers import RowLike
from amortsched.adapters.persistence.relationships import (
    PlannedRelation,
    Relationship,
    RelationshipPlan,
    plan_relations,
)
from amortsched.adapters.persistence.specifications import compile_specification, ensure_no_relations, extract_relations
from amortsched.core.entities import Entity
from amortsched.core.pagination import Paginated, Pagination
from amortsched.core.specifications import Id, Specification


class BaseRepository[T: Entity]:
    _table: ClassVar[Table]
    _from_row: ClassVar[Callable[[RowLike], Any]]
    _to_values: ClassVar[Callable[..., dict[str, object]]]
    _order_column: ClassVar[str] = "created_at"
    _not_found_error: ClassVar[type[Exception]]
    _relationships: ClassVar[dict[str, Relationship]]

    @classmethod
    def _plan_requested_relations(
        cls, specification: Specification[T] | None
    ) -> tuple[Specification[T] | None, RelationshipPlan]:
        filter_spec, relations = extract_relations(specification)
        return filter_spec, plan_relations(cls._relationships, relations)

    @classmethod
    def _build_get_items_statement(cls, filter_spec: Specification[T] | None, limit: int | None = None):
        statement = (
            sqlalchemy.select(cls._table)
            .where(compile_specification(cls._table, filter_spec))
            .order_by(cls._table.c[cls._order_column])
        )
        if limit is not None:
            statement = statement.limit(limit)
        return statement

    @classmethod
    def _build_count_statement(cls, filter_spec: Specification[T] | None):
        return (
            sqlalchemy.select(sqlalchemy.func.count())
            .select_from(cls._table)
            .where(compile_specification(cls._table, filter_spec))
        )

    @classmethod
    def _build_exists_statement(cls, filter_spec: Specification[T] | None):
        return sqlalchemy.select(
            sqlalchemy.exists().where(compile_specification(cls._table, filter_spec)).select_from(cls._table)
        )

    @classmethod
    def _build_paginated_statements(
        cls,
        specification: Specification[T] | None = None,
        pagination: Pagination | None = None,
    ):
        filter_spec, relation_plan = cls._plan_requested_relations(specification)
        where_clause = compile_specification(cls._table, filter_spec)
        statement, limit, offset = build_single_statement_paginated_query(
            cls._table,
            where_clause,
            cls._order_column,
            pagination,
        )
        return statement, limit, offset, relation_plan

    @classmethod
    def _build_delete_statement(cls, filter_spec: Specification[T] | None):
        return sqlalchemy.delete(cls._table).where(compile_specification(cls._table, filter_spec))

    @classmethod
    def _ensure_order_by_supported(cls, order_by: str | Sequence[str] | None) -> None:
        if order_by is not None:
            raise NotImplementedError(f"order_by is not supported by {cls.__name__}")


class AsyncRepository[T: Entity](BaseRepository[T]):
    def __init__(self, session: sqlalchemy.ext.asyncio.AsyncSession) -> None:
        self._session = session

    async def _load_relations(self, items: list[T], relations: list[PlannedRelation]) -> None:
        pass

    async def get_by_id(self, id: UUID, specification: Specification[T] | None = None) -> T | None:
        filter_spec = Id(id) if specification is None else Id(id) & specification
        return await self.get_one_or_none(filter_spec)

    async def get_one(self, specification: Specification[T]) -> T:
        item = await self.get_one_or_none(specification)
        if item is None:
            raise self._not_found_error("matching specification")
        return item

    async def get_one_or_none(self, specification: Specification[T]) -> T | None:
        async for item in self.get_items(specification=specification, limit=1):
            return item
        return None

    async def get_items(
        self,
        specification: Specification[T] | None = None,
        order_by: str | Sequence[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[T]:
        self._ensure_order_by_supported(order_by)
        filter_spec, relation_plan = self._plan_requested_relations(specification)
        statement = self._build_get_items_statement(filter_spec, limit)

        rows = (await self._session.execute(statement)).mappings().all()
        items = [self._from_row(row) for row in rows]
        await self._load_relations(items, relation_plan.joins + relation_plan.select_ins)

        for item in items:
            yield item

    async def get_paginated(
        self,
        specification: Specification[T] | None = None,
        pagination: Pagination | None = None,
    ) -> Paginated[T]:
        self._ensure_order_by_supported(None if pagination is None else pagination.order_by)
        statement, limit, offset, relation_plan = self._build_paginated_statements(specification, pagination)

        rows = (await self._session.execute(statement)).mappings().all()
        items, total = extract_paginated_items_and_total(rows, "id", self._from_row)
        normalized_limit = normalize_paginated_limit(limit, total)
        assert_type(normalized_limit, int)
        await self._load_relations(items, relation_plan.joins + relation_plan.select_ins)
        return Paginated.from_limit_offset(items, total=total, limit=normalized_limit, offset=offset)

    async def count(self, specification: Specification[T] | None = None) -> int:
        filter_spec, _relation_plan = self._plan_requested_relations(specification)
        statement = self._build_count_statement(filter_spec)
        return cast(int, (await self._session.execute(statement)).scalar_one())

    async def exists(self, specification: Specification[T]) -> bool:
        filter_spec, _relation_plan = self._plan_requested_relations(specification)
        statement = self._build_exists_statement(filter_spec)
        return cast(bool, (await self._session.execute(statement)).scalar_one())

    async def add(self, item: T) -> T:
        statement = sqlalchemy.insert(self._table).values(**self._to_values(item))
        await self._session.execute(statement)
        return item

    async def update(self, item: T) -> T:
        statement = sqlalchemy.update(self._table).where(self._table.c.id == item.id).values(**self._to_values(item))
        result = await self._session.execute(statement)
        if result.rowcount == 0:
            raise self._not_found_error(item.id)
        return item

    async def save(self, item: T, conflict_on: Sequence[str] = ("id",)) -> T:
        statement = build_postgres_upsert_statement(self._table, self._to_values(item), conflict_on)
        await self._session.execute(statement)
        return item

    async def delete(self, specification: Specification[T]) -> int:
        ensure_no_relations(specification, "delete")
        filter_spec, _relations = extract_relations(specification)
        statement = self._build_delete_statement(filter_spec)
        result = await self._session.execute(statement)
        return result.rowcount

    async def purge(self, specification: Specification[T]) -> int:
        ensure_no_relations(specification, "purge")
        filter_spec, _relations = extract_relations(specification)
        statement = self._build_delete_statement(filter_spec)
        result = await self._session.execute(statement)
        return result.rowcount
