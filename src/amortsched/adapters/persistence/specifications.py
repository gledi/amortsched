from functools import singledispatch
from typing import Any

import sqlalchemy
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.schema import Table

from amortsched.core.specifications import (
    And,
    Between,
    Contains,
    EndsWith,
    Eq,
    Ge,
    Gt,
    Id,
    In,
    Is,
    IsActive,
    IsDeleted,
    IsFalse,
    IsNone,
    IsTrue,
    Le,
    Like,
    Lt,
    Not,
    Or,
    Rel,
    Specification,
    StartsWith,
)


def compile_specification(table: Table, spec: Specification[Any] | None) -> ColumnElement[bool]:
    if spec is None:
        return sqlalchemy.true()
    return _compile_specification(spec, table)


@singledispatch
def _compile_specification(spec: Specification[Any], table: Table) -> ColumnElement[bool]:
    raise NotImplementedError(f"Unsupported specification operator: {type(spec).__name__}")


@_compile_specification.register
def _(spec: Eq, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field) == spec.value


@_compile_specification.register
def _(spec: Gt, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field) > spec.value


@_compile_specification.register
def _(spec: Lt, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field) < spec.value


@_compile_specification.register
def _(spec: Ge, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field) >= spec.value


@_compile_specification.register
def _(spec: Le, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field) <= spec.value


@_compile_specification.register
def _(spec: In, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).in_(spec.values)


@_compile_specification.register
def _(spec: Between, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).between(spec.lower, spec.upper)


@_compile_specification.register
def _(spec: StartsWith, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).like(f"{_escape_like_value(spec.prefix)}%", escape="\\")


@_compile_specification.register
def _(spec: Contains, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).like(f"%{_escape_like_value(spec.substring)}%", escape="\\")


@_compile_specification.register
def _(spec: EndsWith, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).like(f"%{_escape_like_value(spec.suffix)}", escape="\\")


@_compile_specification.register
def _(spec: Like, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).like(spec.pattern)


@_compile_specification.register
def _(spec: IsNone, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).is_(None)


@_compile_specification.register
def _(spec: Is, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).is_(spec.value)


@_compile_specification.register
def _(spec: IsTrue, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).is_(True)


@_compile_specification.register
def _(spec: IsFalse, table: Table) -> ColumnElement[bool]:
    return _get_column(table, spec.field).is_(False)


@_compile_specification.register
def _(spec: IsDeleted, table: Table) -> ColumnElement[bool]:
    return _get_column(table, "is_deleted").is_(True)


@_compile_specification.register
def _(spec: IsActive, table: Table) -> ColumnElement[bool]:
    return _get_column(table, "is_active").is_(True)


@_compile_specification.register
def _(spec: Id, table: Table) -> ColumnElement[bool]:
    return table.c.id == spec.id


@_compile_specification.register
def _(spec: And, table: Table) -> ColumnElement[bool]:
    return sqlalchemy.and_(
        compile_specification(table, spec.left),
        compile_specification(table, spec.right),
    )


@_compile_specification.register
def _(spec: Or, table: Table) -> ColumnElement[bool]:
    return sqlalchemy.or_(
        compile_specification(table, spec.left),
        compile_specification(table, spec.right),
    )


@_compile_specification.register
def _(spec: Not, table: Table) -> ColumnElement[bool]:
    return sqlalchemy.not_(compile_specification(table, spec.spec))


@_compile_specification.register
def _(spec: Rel, table: Table) -> ColumnElement[bool]:
    del spec, table
    raise ValueError("Rel specifications must be extracted before compilation")


def extract_relations(spec: Specification[Any] | None) -> tuple[Specification[Any] | None, list[Rel[Any]]]:
    if spec is None:
        return None, []
    if isinstance(spec, Rel):
        _validate_relation_spec(spec)
        return None, [spec]
    if isinstance(spec, And):
        left_spec, left_relations = extract_relations(spec.left)
        right_spec, right_relations = extract_relations(spec.right)
        relations = left_relations + right_relations
        if left_spec is None and right_spec is None:
            return None, relations
        if left_spec is None:
            return right_spec, relations
        if right_spec is None:
            return left_spec, relations
        return And(left_spec, right_spec), relations
    if isinstance(spec, Or):
        _raise_if_contains_relation(spec.left, "Or")
        _raise_if_contains_relation(spec.right, "Or")
        return spec, []
    if isinstance(spec, Not):
        _raise_if_contains_relation(spec.spec, "Not")
        return spec, []
    return spec, []


def ensure_no_relations(spec: Specification[Any] | None, operation: str) -> None:
    if spec is not None and _contains_relation(spec):
        raise ValueError(f"{operation}() does not support Rel specifications")


def _raise_if_contains_relation(spec: Specification[Any], context: str) -> None:
    if _contains_relation(spec):
        raise ValueError(
            "Rel specifications are only supported at the top level or inside And expressions; "
            f"found Rel inside {context}"
        )


def _validate_relation_spec(spec: Rel[Any]) -> None:
    if spec.spec is not None and _contains_relation(spec.spec):
        raise ValueError(
            "Nested relation loading is not supported by the SQLAlchemy adapter; "
            f"relation '{spec.relation}' contains another Rel specification"
        )


def _contains_relation(spec: Specification[Any]) -> bool:
    if isinstance(spec, Rel):
        return True
    if isinstance(spec, And | Or):
        return _contains_relation(spec.left) or _contains_relation(spec.right)
    if isinstance(spec, Not):
        return _contains_relation(spec.spec)
    return False


def _get_column(table: Table, field: str):
    if field not in table.c:
        raise ValueError(f"Unknown column '{field}' for table '{table.name}'")
    return table.c[field]


def _escape_like_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


__all__ = ["compile_specification", "ensure_no_relations", "extract_relations"]
