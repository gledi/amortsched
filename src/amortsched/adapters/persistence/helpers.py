from collections.abc import Sequence
from typing import Any, cast

import sqlalchemy
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from amortsched.core.pagination import LimitOffset, PageSize, Pagination

_TOTAL_COUNT_LABEL = "_amortsched_total_count"


def build_postgres_upsert_statement(table, values: dict[str, object], conflict_columns: Sequence[str]):
    insert_statement = postgresql_insert(table).values(**values)
    conflict_set = set(conflict_columns)
    update_values = {
        column.name: insert_statement.excluded[column.name] for column in table.c if column.name not in conflict_set
    }
    return insert_statement.on_conflict_do_update(
        index_elements=[table.c[name] for name in conflict_columns],
        set_=update_values,
    )


def build_single_statement_paginated_query(
    table, where_clause: Any, order_column_name: str, pagination: Pagination | None
):
    requested_limit, offset = _resolve_limit_offset(pagination)
    filtered = (
        sqlalchemy.select(*table.c, sqlalchemy.func.count().over().label(_TOTAL_COUNT_LABEL))
        .where(where_clause)
        .subquery()
    )
    page = (
        sqlalchemy.select(
            *[filtered.c[column.name] for column in table.c],
            filtered.c[_TOTAL_COUNT_LABEL],
        )
        .select_from(filtered)
        .order_by(filtered.c[order_column_name])
    )
    if requested_limit is not None:
        page = page.limit(requested_limit).offset(offset)
    page = page.subquery()

    summary = sqlalchemy.select(
        sqlalchemy.func.coalesce(sqlalchemy.func.max(filtered.c[_TOTAL_COUNT_LABEL]), 0).label(_TOTAL_COUNT_LABEL)
    ).subquery()

    statement = (
        sqlalchemy.select(
            *[page.c[column.name] for column in table.c],
            summary.c[_TOTAL_COUNT_LABEL],
        )
        .select_from(summary.outerjoin(page, sqlalchemy.true()))
        .order_by(page.c[order_column_name].nulls_last())
    )
    return statement, requested_limit, offset


def extract_paginated_items_and_total(rows: Sequence[Any], item_id_column_name: str, item_factory):
    if not rows:
        return [], 0

    total = cast(int, rows[0][_TOTAL_COUNT_LABEL])
    items = [item_factory(row) for row in rows if row[item_id_column_name] is not None]
    return items, total


def normalize_paginated_limit(limit: int | None, total: int) -> int:
    if limit is None:
        return total
    return cast(int, limit)


def _resolve_limit_offset(pagination: Pagination | None) -> tuple[int | None, int]:
    match pagination:
        case PageSize(page=page, size=size):
            return size, (page - 1) * size
        case LimitOffset(limit=limit, offset=offset):
            return limit, offset
        case None:
            return None, 0
