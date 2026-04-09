import re
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

    def is_satisfied_by(self, candidate: T) -> bool:
        raise NotImplementedError("Subclasses must implement is_satisfied_by()")

    def __call__(self, candidate: T) -> bool:
        return self.is_satisfied_by(candidate)


@dataclass(frozen=True, slots=True)
class And[T](Specification[T]):
    left: Specification[T]
    right: Specification[T]

    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)


@dataclass(frozen=True, slots=True)
class Or[T](Specification[T]):
    left: Specification[T]
    right: Specification[T]

    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)


@dataclass(frozen=True, slots=True)
class Not[T](Specification[T]):
    spec: Specification[T]

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self.spec.is_satisfied_by(candidate)


@dataclass(frozen=True, slots=True)
class Eq[T](Specification[T]):
    field: str
    value: Any

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) == self.value


@dataclass(frozen=True, slots=True)
class Gt[T](Specification[T]):
    field: str
    value: Any

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) > self.value


@dataclass(frozen=True, slots=True)
class Lt[T](Specification[T]):
    field: str
    value: Any

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) < self.value


@dataclass(frozen=True, slots=True)
class Ge[T](Specification[T]):
    field: str
    value: Any

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) >= self.value


@dataclass(frozen=True, slots=True)
class Le[T](Specification[T]):
    field: str
    value: Any

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) <= self.value


@dataclass(frozen=True, slots=True)
class In[T](Specification[T]):
    field: str
    values: Sequence[Any]

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) in self.values


@dataclass(frozen=True, slots=True)
class Between[T](Specification[T]):
    field: str
    lower: Any
    upper: Any

    def is_satisfied_by(self, candidate: T) -> bool:
        value = getattr(candidate, self.field)
        return self.lower <= value <= self.upper


@dataclass(frozen=True, slots=True)
class StartsWith[T](Specification[T]):
    field: str
    prefix: str

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field).startswith(self.prefix)


@dataclass(frozen=True, slots=True)
class Contains[T](Specification[T]):
    field: str
    substring: str

    def is_satisfied_by(self, candidate: T) -> bool:
        return self.substring in getattr(candidate, self.field)


@dataclass(frozen=True, slots=True)
class EndsWith[T](Specification[T]):
    field: str
    suffix: str

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field).endswith(self.suffix)


@dataclass(frozen=True, slots=True)
class Like[T](Specification[T]):
    field: str
    pattern: str

    def is_satisfied_by(self, candidate: T) -> bool:
        re_pattern = self.pattern.replace("%", ".*").replace("_", ".")
        return re.match(re_pattern, getattr(candidate, self.field)) is not None


@dataclass(frozen=True, slots=True)
class IsNone[T](Specification[T]):
    field: str

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) is None


@dataclass(frozen=True, slots=True)
class Is[T](Specification[T]):
    field: str
    value: bool

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) is self.value


@dataclass(frozen=True, slots=True)
class IsTrue[T](Specification[T]):
    field: str

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) is True


@dataclass(frozen=True, slots=True)
class IsFalse[T](Specification[T]):
    field: str

    def is_satisfied_by(self, candidate: T) -> bool:
        return getattr(candidate, self.field) is False


@dataclass(frozen=True, slots=True)
class IsDeleted[T](Specification[T]):
    def is_satisfied_by(self, candidate: T) -> bool:
        return candidate.is_deleted is True  # pyright: ignore[reportAttributeAccessIssue]


@dataclass(frozen=True, slots=True)
class IsActive[T](Specification[T]):
    def is_satisfied_by(self, candidate: T) -> bool:
        return candidate.is_deleted is False  # pyright: ignore[reportAttributeAccessIssue]


@dataclass(frozen=True, slots=True)
class Id[T](Specification[T]):
    id: Any

    def is_satisfied_by(self, candidate: T) -> bool:
        return candidate.id == self.id  # pyright: ignore[reportAttributeAccessIssue]


@dataclass(frozen=True, slots=True)
class With[T](Specification[T]):
    """Filter loaded related entities and ensure we load them.

    ``With("payments", ~IsDeleted())`` tells the repository to load the payments relation,
    but only include payments that are not deleted.
    Useful for ensuring we load the related entities we need for our use case,
    without having to load everything and filter in memory.

    Examples:
        Load all related payments, no other filtering happening to the related payments
        `With("payments")`

        Load all active related payments
        `With("payments", IsActive())`

        Load all related not-deleted sections and then further filter the related queries of those sections to only
        include asset queries that are not deleted
        `With("sections", ~IsDeleted() & With("queries", IsAsset() & ~IsDeleted()))`
    """

    relation: str
    spec: Specification[Any] | None = None

    def is_satisfied_by(self, candidate: T) -> bool:
        """
        This specification is used to know which related entities to load, it doesn't filter the main entity.
        Since the main entity is always loaded, this specification is always satisfied. The filtering happens in the
        related entities, not in the main entity.
        """
        return True
