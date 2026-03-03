from dataclasses import dataclass
from uuid import UUID, uuid7

import pytest
from amortsched.core.specifications import Eq, Gt, Id, In, Le, Lt, Rel
from amortsched.data.inmemory.filters import extract_rels, to_filter


@dataclass
class FakeItem:
    id: UUID
    name: str
    age: int
    email: str


@pytest.fixture
def items():
    return [
        FakeItem(id=uuid7(), name="Alice", age=30, email="alice@example.com"),
        FakeItem(id=uuid7(), name="Bob", age=25, email="bob@example.com"),
        FakeItem(id=uuid7(), name="Charlie", age=35, email="charlie@example.com"),
    ]


def test_to_filter_eq(items):
    predicate = to_filter(Eq("name", "Bob"))
    result = [x for x in items if predicate(x)]
    assert len(result) == 1
    assert result[0].name == "Bob"


def test_to_filter_gt(items):
    predicate = to_filter(Gt("age", 28))
    result = [x for x in items if predicate(x)]
    assert len(result) == 2
    assert {x.name for x in result} == {"Alice", "Charlie"}


def test_to_filter_lt(items):
    predicate = to_filter(Lt("age", 30))
    result = [x for x in items if predicate(x)]
    assert len(result) == 1
    assert result[0].name == "Bob"


def test_to_filter_le(items):
    predicate = to_filter(Le("age", 30))
    result = [x for x in items if predicate(x)]
    assert len(result) == 2


def test_to_filter_and(items):
    predicate = to_filter(Eq("name", "Alice") & Gt("age", 25))
    result = [x for x in items if predicate(x)]
    assert len(result) == 1
    assert result[0].name == "Alice"


def test_to_filter_or(items):
    predicate = to_filter(Eq("name", "Alice") | Eq("name", "Bob"))
    result = [x for x in items if predicate(x)]
    assert len(result) == 2


def test_to_filter_not(items):
    predicate = to_filter(~Eq("name", "Alice"))
    result = [x for x in items if predicate(x)]
    assert len(result) == 2
    assert all(x.name != "Alice" for x in result)


def test_to_filter_id(items):
    target = items[1]
    predicate = to_filter(Id(target.id))
    result = [x for x in items if predicate(x)]
    assert len(result) == 1
    assert result[0] is target


def test_to_filter_in(items):
    predicate = to_filter(In("name", ["Alice", "Charlie"]))
    result = [x for x in items if predicate(x)]
    assert len(result) == 2
    assert {x.name for x in result} == {"Alice", "Charlie"}


def test_to_filter_none_spec_matches_all(items):
    predicate = to_filter(None)
    result = [x for x in items if predicate(x)]
    assert len(result) == 3


def test_extract_rels_none_returns_empty():
    spec, rels = extract_rels(None)
    assert spec is None
    assert rels == []


def test_extract_rels_single_rel():
    spec, rels = extract_rels(Rel("plans"))
    assert spec is None
    assert len(rels) == 1
    assert rels[0].relation == "plans"


def test_extract_rels_filter_and_rel():
    combined = Eq("name", "Alice") & Rel("plans")
    spec, rels = extract_rels(combined)
    assert isinstance(spec, Eq)
    assert spec.field == "name"
    assert len(rels) == 1
    assert rels[0].relation == "plans"


def test_extract_rels_multiple_rels():
    combined = Rel("plans") & Rel("schedules")
    spec, rels = extract_rels(combined)
    assert spec is None
    assert len(rels) == 2
    assert {r.relation for r in rels} == {"plans", "schedules"}


def test_extract_rels_filter_only():
    eq = Eq("name", "Alice")
    spec, rels = extract_rels(eq)
    assert spec is eq
    assert rels == []


def test_extract_rels_nested_and_with_rel():
    combined = Eq("name", "Alice") & Eq("age", 30) & Rel("plans")
    spec, rels = extract_rels(combined)
    assert len(rels) == 1
    assert rels[0].relation == "plans"
    # remaining spec should still filter correctly
    predicate = to_filter(spec)
    assert predicate(FakeItem(id=uuid7(), name="Alice", age=30, email="a@b.com"))
    assert not predicate(FakeItem(id=uuid7(), name="Bob", age=30, email="b@b.com"))


def test_extract_rels_rel_with_sub_spec():
    combined = Eq("is_active", True) & Rel("plans", ~Eq("is_deleted", True))
    spec, rels = extract_rels(combined)
    assert isinstance(spec, Eq)
    assert len(rels) == 1
    assert rels[0].relation == "plans"
    assert rels[0].spec is not None


def test_extract_rels_rel_inside_or_is_preserved():
    combined = Eq("name", "Alice") & (Rel("plans") | Eq("age", 30))
    spec, rels = extract_rels(combined)
    assert rels == []
    assert spec is not None


def test_extract_rels_rel_inside_not_is_preserved():
    combined = Eq("name", "Alice") & ~Rel("plans")
    spec, rels = extract_rels(combined)
    assert rels == []
    assert spec is not None
