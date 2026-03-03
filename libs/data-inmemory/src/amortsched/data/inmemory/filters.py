"""Specification-to-predicate conversion for in-memory repositories."""

import re
from collections.abc import Callable
from functools import singledispatch
from typing import Any

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


@singledispatch
def to_filter[T](spec: Specification[T] | None) -> Callable[[T], bool]:
    """Convert a Specification to a predicate function.

    Returns a callable that takes a single item and returns True if it matches.
    """
    if spec is None:
        return lambda _: True
    raise NotImplementedError(f"No filter registered for {type(spec).__name__}")


@to_filter.register
def _eq(spec: Eq) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field) == spec.value


@to_filter.register
def _gt(spec: Gt) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field) > spec.value


@to_filter.register
def _lt(spec: Lt) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field) < spec.value


@to_filter.register
def _ge(spec: Ge) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field) >= spec.value


@to_filter.register
def _le(spec: Le) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field) <= spec.value


@to_filter.register
def _in(spec: In) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field) in spec.values


@to_filter.register
def _between(spec: Between) -> Callable[[Any], bool]:
    return lambda item: spec.lower <= getattr(item, spec.field) <= spec.upper


@to_filter.register
def _starts_with(spec: StartsWith) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field, "").startswith(spec.prefix)


@to_filter.register
def _contains(spec: Contains) -> Callable[[Any], bool]:
    return lambda item: spec.substring in getattr(item, spec.field, "")


@to_filter.register
def _ends_with(spec: EndsWith) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field, "").endswith(spec.suffix)


@to_filter.register
def _like(spec: Like) -> Callable[[Any], bool]:
    parts = re.split(r"(%|_)", spec.pattern)
    regex_parts = []
    for part in parts:
        if part == "%":
            regex_parts.append(".*")
        elif part == "_":
            regex_parts.append(".")
        else:
            regex_parts.append(re.escape(part))
    regex = re.compile("^" + "".join(regex_parts) + "$")
    return lambda item: bool(regex.match(getattr(item, spec.field, "")))


@to_filter.register
def _is_none(spec: IsNone) -> Callable[[Any], bool]:
    return lambda item: getattr(item, spec.field) is None


@to_filter.register
def _is(spec: Is) -> Callable[[Any], bool]:
    return lambda item: bool(getattr(item, spec.field)) == spec.value


@to_filter.register
def _is_true(spec: IsTrue) -> Callable[[Any], bool]:
    return lambda item: bool(getattr(item, spec.field)) is True


@to_filter.register
def _is_false(spec: IsFalse) -> Callable[[Any], bool]:
    return lambda item: bool(getattr(item, spec.field)) is False


@to_filter.register
def _is_deleted(spec: IsDeleted) -> Callable[[Any], bool]:
    return lambda item: getattr(item, "is_deleted", False)


@to_filter.register
def _is_active(spec: IsActive) -> Callable[[Any], bool]:
    return lambda item: getattr(item, "is_active", True)


@to_filter.register
def _id(spec: Id) -> Callable[[Any], bool]:
    return lambda item: item.id == spec.id


@to_filter.register
def _and(spec: And) -> Callable[[Any], bool]:
    left = to_filter(spec.left)
    right = to_filter(spec.right)
    return lambda item: left(item) and right(item)


@to_filter.register
def _or(spec: Or) -> Callable[[Any], bool]:
    left = to_filter(spec.left)
    right = to_filter(spec.right)
    return lambda item: left(item) or right(item)


@to_filter.register
def _not(spec: Not) -> Callable[[Any], bool]:
    inner = to_filter(spec.spec)
    return lambda item: not inner(item)


def extract_rels[T](spec: Specification[T] | None) -> tuple[Specification[T] | None, list[Rel]]:
    """Extract Rel nodes from a specification tree.

    Walks And branches, strips Rel nodes, returns (remaining_filter_spec, rels).
    Rels inside Or/Not are left in place (not logically meaningful as loading hints).
    """
    if spec is None:
        return None, []
    if isinstance(spec, Rel):
        return None, [spec]
    if isinstance(spec, And):
        left_spec, left_rels = extract_rels(spec.left)
        right_spec, right_rels = extract_rels(spec.right)
        rels = left_rels + right_rels
        if left_spec is None and right_spec is None:
            return None, rels
        if left_spec is None:
            return right_spec, rels
        if right_spec is None:
            return left_spec, rels
        return And(left_spec, right_spec), rels
    return spec, []
