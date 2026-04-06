from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Specification[T]:
    def __and__(self, other: Specification[T]) -> Specification[T]:
        return And(self, other)

    def __or__(self, other: Specification[T]) -> Specification[T]:
        return Or(self, other)

    def __invert__(self) -> Specification[T]:
        return Not(self)


@dataclass(frozen=True, slots=True)
class And[T](Specification[T]):
    left: Specification[T]
    right: Specification[T]


@dataclass(frozen=True, slots=True)
class Or[T](Specification[T]):
    left: Specification[T]
    right: Specification[T]


@dataclass(frozen=True, slots=True)
class Not[T](Specification[T]):
    spec: Specification[T]


@dataclass(frozen=True, slots=True)
class Eq[T](Specification[T]):
    field: str
    value: Any


@dataclass(frozen=True, slots=True)
class Gt[T](Specification[T]):
    field: str
    value: Any


@dataclass(frozen=True, slots=True)
class Lt[T](Specification[T]):
    field: str
    value: Any


@dataclass(frozen=True, slots=True)
class Ge[T](Specification[T]):
    field: str
    value: Any


@dataclass(frozen=True, slots=True)
class Le[T](Specification[T]):
    field: str
    value: Any


@dataclass(frozen=True, slots=True)
class In[T](Specification[T]):
    field: str
    values: Sequence[Any]


@dataclass(frozen=True, slots=True)
class Between[T](Specification[T]):
    field: str
    lower: Any
    upper: Any


@dataclass(frozen=True, slots=True)
class StartsWith[T](Specification[T]):
    field: str
    prefix: str


@dataclass(frozen=True, slots=True)
class Contains[T](Specification[T]):
    field: str
    substring: str


@dataclass(frozen=True, slots=True)
class EndsWith[T](Specification[T]):
    field: str
    suffix: str


@dataclass(frozen=True, slots=True)
class Like[T](Specification[T]):
    field: str
    pattern: str


@dataclass(frozen=True, slots=True)
class IsNone[T](Specification[T]):
    field: str


@dataclass(frozen=True, slots=True)
class Is[T](Specification[T]):
    field: str
    value: bool


@dataclass(frozen=True, slots=True)
class IsTrue[T](Specification[T]):
    field: str


@dataclass(frozen=True, slots=True)
class IsFalse[T](Specification[T]):
    field: str


@dataclass(frozen=True, slots=True)
class IsDeleted[T](Specification[T]): ...


@dataclass(frozen=True, slots=True)
class IsActive[T](Specification[T]): ...


@dataclass(frozen=True, slots=True)
class Id[T](Specification[T]):
    id: Any


@dataclass(frozen=True, slots=True)
class Rel[T](Specification[T]):
    """Filter loaded related entities and ensure we load them.

    ``Rel("payments", ~IsDeleted())`` tells the repository to load the payments relation, but only include payments that
    are not deleted. Useful for ensuring we load the related entities we need for our use case, without having to load
    everything and filter in memory.

    Examples:
        Load all related payments, no other filtering happening to the related payments
        `Rel("payments")`

        Load all active related payments
        `Rel("payments", IsActive())`

        Load all related not-deleted sections and then further filter the related queries of those sections to only
        include asset queries that are not deleted
        `Rel("sections", ~IsDeleted() & Rel("queries", IsAsset() & ~IsDeleted()))`
    """

    relation: str
    spec: Specification[Any] | None = None
