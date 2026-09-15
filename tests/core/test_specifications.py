from dataclasses import dataclass

from amortsched.core.specifications import (
    Eq,
    In,
    IsActive,
    IsDeleted,
    IsNotDeleted,
    Not,
)


@dataclass
class DummyUser:
    id: str
    is_active: bool


@dataclass
class DummyPlan:
    id: str
    is_deleted: bool


def test_is_active_checks_is_active_attribute():
    active_user = DummyUser(id="1", is_active=True)
    inactive_user = DummyUser(id="2", is_active=False)

    spec = IsActive()
    assert spec.is_satisfied_by(active_user) is True
    assert spec.is_satisfied_by(inactive_user) is False


def test_is_deleted_and_is_not_deleted():
    deleted_plan = DummyPlan(id="1", is_deleted=True)
    active_plan = DummyPlan(id="2", is_deleted=False)

    assert IsDeleted().is_satisfied_by(deleted_plan) is True
    assert IsDeleted().is_satisfied_by(active_plan) is False

    assert IsNotDeleted().is_satisfied_by(deleted_plan) is False
    assert IsNotDeleted().is_satisfied_by(active_plan) is True


def test_spec_composition():
    u1 = DummyUser(id="admin", is_active=True)
    u2 = DummyUser(id="guest", is_active=True)
    u3 = DummyUser(id="admin", is_active=False)

    spec = Eq("id", "admin") & IsActive()
    assert spec(u1) is True
    assert spec(u2) is False
    assert spec(u3) is False

    or_spec = Eq("id", "guest") | Not(IsActive())
    assert or_spec(u1) is False
    assert or_spec(u2) is True
    assert or_spec(u3) is True


def test_in_spec():
    u = DummyUser(id="2", is_active=True)
    assert In("id", ["1", "2", "3"])(u) is True
    assert In("id", ["4", "5"])(u) is False
