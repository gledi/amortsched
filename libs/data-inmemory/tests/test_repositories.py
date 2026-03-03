import datetime
from decimal import Decimal
from uuid import UUID, uuid7

import pytest
from amortsched.core.entities import Plan, Profile, User
from amortsched.core.errors import (
    DuplicateEmailError,
    PlanNotFoundError,
    ProfileNotFoundError,
    ScheduleNotFoundError,
    UserNotFoundError,
)
from amortsched.core.pagination import LimitOffset
from amortsched.core.specifications import Eq, Id, Rel
from amortsched.core.values import Term
from amortsched.data.inmemory.repositories import (
    InMemoryPlanRepository,
    InMemoryScheduleRepository,
    InMemoryUserProfileRepository,
    InMemoryUserRepository,
)
from amortsched.data.inmemory.store import InMemoryStore

_FAKE_USER_ID_1 = UUID("01945b88-4f4a-7000-8000-000000000001")
_FAKE_USER_ID_2 = UUID("01945b88-4f4a-7000-8000-000000000002")
_FAKE_USER_ID_3 = UUID("01945b88-4f4a-7000-8000-000000000003")


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def user_repo(store):
    return InMemoryUserRepository(store)


@pytest.fixture
def plan_repo(store):
    return InMemoryPlanRepository(store)


@pytest.fixture
def schedule_repo(store):
    return InMemoryScheduleRepository(store)


@pytest.fixture
def profile_repo(store):
    return InMemoryUserProfileRepository(store)


# --- User repository tests ---


def test_user_repo_add_and_get_by_id(user_repo):
    user = User(email="a@b.com", name="A B", password_hash="hashed")
    user_repo.add(user)
    fetched = user_repo.get_by_id(user.id)
    assert fetched is user


def test_user_repo_get_by_id_returns_none_for_missing(user_repo):
    assert user_repo.get_by_id(uuid7()) is None


def test_user_repo_get_one_by_email(user_repo):
    user = User(email="a@b.com", name="A B", password_hash="hashed")
    user_repo.add(user)
    fetched = user_repo.get_one(Eq("email", "a@b.com"))
    assert fetched is user


def test_user_repo_get_one_raises_not_found(user_repo):
    with pytest.raises(UserNotFoundError):
        user_repo.get_one(Eq("email", "missing@example.com"))


def test_user_repo_get_one_or_none_returns_none(user_repo):
    result = user_repo.get_one_or_none(Eq("email", "missing@example.com"))
    assert result is None


def test_user_repo_duplicate_email_raises(user_repo):
    user1 = User(email="a@b.com", name="A", password_hash="hashed")
    user2 = User(email="a@b.com", name="B", password_hash="hashed2")
    user_repo.add(user1)
    with pytest.raises(DuplicateEmailError) as exc_info:
        user_repo.add(user2)
    assert exc_info.value.email == "a@b.com"


def test_user_repo_delete_by_id(user_repo):
    user = User(email="a@b.com", name="A B", password_hash="hashed")
    user_repo.add(user)
    count = user_repo.delete(Id(user.id))
    assert count == 1
    assert user_repo.get_by_id(user.id) is None


def test_user_repo_delete_returns_zero_for_missing(user_repo):
    count = user_repo.delete(Id(uuid7()))
    assert count == 0


def test_user_repo_get_items_all(user_repo):
    user1 = User(email="a@b.com", name="A", password_hash="hashed")
    user2 = User(email="c@d.com", name="C", password_hash="hashed")
    user_repo.add(user1)
    user_repo.add(user2)
    all_users = list(user_repo.get_items())
    assert len(all_users) == 2
    assert {u.id for u in all_users} == {user1.id, user2.id}


def test_user_repo_get_items_with_spec(user_repo):
    user1 = User(email="a@b.com", name="A", password_hash="hashed")
    user2 = User(email="c@d.com", name="C", password_hash="hashed")
    user_repo.add(user1)
    user_repo.add(user2)
    result = list(user_repo.get_items(Eq("name", "A")))
    assert len(result) == 1
    assert result[0] is user1


def test_user_repo_count(user_repo):
    user_repo.add(User(email="a@b.com", name="A", password_hash="h"))
    user_repo.add(User(email="b@b.com", name="B", password_hash="h"))
    assert user_repo.count() == 2
    assert user_repo.count(Eq("name", "A")) == 1


def test_user_repo_exists(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    assert user_repo.exists(Eq("email", "a@b.com")) is True
    assert user_repo.exists(Eq("email", "z@z.com")) is False


def test_user_repo_update(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    user.name = "Updated"
    updated = user_repo.update(user)
    assert updated.name == "Updated"
    assert user_repo.get_by_id(user.id).name == "Updated"


def test_user_repo_update_not_found_raises(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    with pytest.raises(UserNotFoundError):
        user_repo.update(user)


def test_user_repo_save_existing(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    user.name = "Saved"
    saved = user_repo.save(user)
    assert saved.name == "Saved"


def test_user_repo_save_new(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    saved = user_repo.save(user)
    assert saved is user
    assert user_repo.get_by_id(user.id) is user


def test_user_repo_get_paginated(user_repo):
    for i in range(5):
        user_repo.add(User(email=f"u{i}@b.com", name=f"User {i}", password_hash="h"))
    result = user_repo.get_paginated(pagination=LimitOffset(limit=2, offset=0))
    assert len(result.items) == 2
    assert result.meta.total == 5
    assert result.meta.limit == 2
    assert result.meta.offset == 0


def test_user_repo_purge(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    count = user_repo.purge(Id(user.id))
    assert count == 1
    assert user_repo.get_by_id(user.id) is None


def test_user_repo_get_items_with_limit(user_repo):
    for i in range(5):
        user_repo.add(User(email=f"u{i}@b.com", name=f"User {i}", password_hash="h"))
    items = list(user_repo.get_items(limit=3))
    assert len(items) == 3


def test_user_repo_delete_allows_reuse_of_email(user_repo):
    user1 = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user1)
    user_repo.delete(Id(user1.id))
    user2 = User(email="a@b.com", name="B", password_hash="h2")
    user_repo.add(user2)
    assert user_repo.get_by_id(user2.id) is user2


def test_user_repo_update_duplicate_email_raises(user_repo):
    user1 = User(email="a@b.com", name="A", password_hash="h")
    user2 = User(email="c@d.com", name="C", password_hash="h")
    user_repo.add(user1)
    user_repo.add(user2)
    user2.email = "a@b.com"
    with pytest.raises(DuplicateEmailError):
        user_repo.update(user2)


# --- Plan repository tests ---


def _make_plan(user_id: UUID, name: str = "Test Plan") -> Plan:
    return Plan(
        user_id=user_id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        amount=Decimal("1000"),
        term=Term(1),
        interest_rate=Decimal("10"),
        start_date=datetime.date(2025, 1, 1),
    )


def test_plan_repo_add_and_get_by_id(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    plan_repo.add(plan)
    fetched = plan_repo.get_by_id(plan.id)
    assert fetched is plan


def test_plan_repo_get_by_id_returns_none_for_missing(plan_repo):
    assert plan_repo.get_by_id(uuid7()) is None


def test_plan_repo_get_one_raises_not_found(plan_repo):
    with pytest.raises(PlanNotFoundError):
        plan_repo.get_one(Id(uuid7()))


def test_plan_repo_update(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    plan_repo.add(plan)
    plan.name = "Updated"
    plan_repo.update(plan)
    fetched = plan_repo.get_by_id(plan.id)
    assert fetched.name == "Updated"


def test_plan_repo_update_not_found_raises(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    with pytest.raises(PlanNotFoundError):
        plan_repo.update(plan)


def test_plan_repo_delete_by_id(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    plan_repo.add(plan)
    count = plan_repo.delete(Id(plan.id))
    assert count == 1
    assert plan_repo.get_by_id(plan.id) is None


def test_plan_repo_delete_returns_zero_for_missing(plan_repo):
    count = plan_repo.delete(Id(uuid7()))
    assert count == 0


def test_plan_repo_get_items_by_user(plan_repo):
    plan1 = _make_plan(_FAKE_USER_ID_1, "Plan A")
    plan2 = _make_plan(_FAKE_USER_ID_1, "Plan B")
    plan3 = _make_plan(_FAKE_USER_ID_2, "Plan C")
    plan_repo.add(plan1)
    plan_repo.add(plan2)
    plan_repo.add(plan3)

    u1_plans = list(plan_repo.get_items(Eq("user_id", _FAKE_USER_ID_1)))
    assert len(u1_plans) == 2
    assert all(p.user_id == _FAKE_USER_ID_1 for p in u1_plans)

    u2_plans = list(plan_repo.get_items(Eq("user_id", _FAKE_USER_ID_2)))
    assert len(u2_plans) == 1
    assert u2_plans[0].name == "Plan C"

    assert list(plan_repo.get_items(Eq("user_id", _FAKE_USER_ID_3))) == []


def test_plan_repo_count(plan_repo):
    plan_repo.add(_make_plan(_FAKE_USER_ID_1, "A"))
    plan_repo.add(_make_plan(_FAKE_USER_ID_1, "B"))
    plan_repo.add(_make_plan(_FAKE_USER_ID_2, "C"))
    assert plan_repo.count() == 3
    assert plan_repo.count(Eq("user_id", _FAKE_USER_ID_1)) == 2


def test_plan_repo_exists(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    plan_repo.add(plan)
    assert plan_repo.exists(Id(plan.id)) is True
    assert plan_repo.exists(Id(uuid7())) is False


def test_plan_repo_get_paginated(plan_repo):
    for i in range(5):
        plan_repo.add(_make_plan(_FAKE_USER_ID_1, f"Plan {i}"))
    result = plan_repo.get_paginated(pagination=LimitOffset(limit=2, offset=1))
    assert len(result.items) == 2
    assert result.meta.total == 5
    assert result.meta.limit == 2
    assert result.meta.offset == 1


def test_plan_repo_purge(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    plan_repo.add(plan)
    count = plan_repo.purge(Id(plan.id))
    assert count == 1
    assert plan_repo.get_by_id(plan.id) is None


def test_plan_repo_get_one_or_none_returns_none(plan_repo):
    result = plan_repo.get_one_or_none(Id(uuid7()))
    assert result is None


def test_plan_repo_save_new(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    saved = plan_repo.save(plan)
    assert saved is plan
    assert plan_repo.get_by_id(plan.id) is plan


def test_plan_repo_save_existing(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    plan_repo.add(plan)
    plan.name = "Updated via save"
    saved = plan_repo.save(plan)
    assert saved.name == "Updated via save"
    assert plan_repo.get_by_id(plan.id).name == "Updated via save"


# --- Rel loading tests ---


def test_user_repo_loads_plans_with_rel(user_repo, plan_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id, "Plan A")
    plan_repo.add(plan)

    fetched = user_repo.get_by_id(user.id, Rel("plans"))
    assert len(fetched.plans) == 1
    assert fetched.plans[0] is plan


def test_user_repo_no_plans_without_rel(user_repo, plan_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id, "Plan A")
    plan_repo.add(plan)

    fetched = user_repo.get_by_id(user.id)
    assert fetched.plans == []


def test_user_repo_loads_plans_filtered_by_rel_spec(user_repo, plan_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan_a = _make_plan(user.id, "Plan A")
    plan_b = _make_plan(user.id, "Plan B")
    plan_b.is_deleted = True
    plan_repo.add(plan_a)
    plan_repo.add(plan_b)

    fetched = user_repo.get_by_id(user.id, Rel("plans", ~Eq("is_deleted", True)))
    assert len(fetched.plans) == 1
    assert fetched.plans[0] is plan_a


def test_plan_repo_loads_user_with_rel(user_repo, plan_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)

    fetched = plan_repo.get_by_id(plan.id, Rel("user"))
    assert fetched.user is user


def test_plan_repo_no_user_without_rel(user_repo, plan_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)

    fetched = plan_repo.get_by_id(plan.id)
    assert fetched._user is None


def test_user_repo_unknown_rel_raises(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)

    with pytest.raises(ValueError, match="Unknown relationship"):
        user_repo.get_by_id(user.id, Rel("nonexistent"))


def test_plan_repo_unknown_rel_raises(plan_repo):
    plan = _make_plan(_FAKE_USER_ID_1)
    plan_repo.add(plan)

    with pytest.raises(ValueError, match="Unknown relationship"):
        plan_repo.get_by_id(plan.id, Rel("nonexistent"))


def test_user_repo_get_items_with_rel(user_repo, plan_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)

    users = list(user_repo.get_items(Rel("plans")))
    assert len(users) == 1
    assert len(users[0].plans) == 1


def test_plan_repo_get_one_with_rel(user_repo, plan_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id, "My Plan")
    plan_repo.add(plan)

    fetched = plan_repo.get_one(Eq("name", "My Plan") & Rel("user"))
    assert fetched.user is user


# --- Schedule repository tests ---


def test_schedule_repo_add_and_get_by_id(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    schedule = plan.generate()
    schedule_repo.add(schedule)
    fetched = schedule_repo.get_by_id(schedule.id)
    assert fetched is schedule


def test_schedule_repo_get_by_id_returns_none(schedule_repo):
    assert schedule_repo.get_by_id(uuid7()) is None


def test_schedule_repo_get_items_by_plan(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    s1 = plan.generate()
    s2 = plan.generate()
    schedule_repo.add(s1)
    schedule_repo.add(s2)
    items = list(schedule_repo.get_items(Eq("plan_id", plan.id)))
    assert len(items) == 2


def test_schedule_repo_delete_by_id(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    schedule = plan.generate()
    schedule_repo.add(schedule)
    count = schedule_repo.delete(Id(schedule.id))
    assert count == 1
    assert schedule_repo.get_by_id(schedule.id) is None


def test_schedule_repo_update(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    schedule = plan.generate()
    schedule_repo.add(schedule)
    schedule.is_deleted = True
    updated = schedule_repo.update(schedule)
    assert updated.is_deleted is True


def test_schedule_repo_update_not_found(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    schedule = plan.generate()
    with pytest.raises(ScheduleNotFoundError):
        schedule_repo.update(schedule)


def test_schedule_repo_count(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    schedule_repo.add(plan.generate())
    schedule_repo.add(plan.generate())
    assert schedule_repo.count() == 2
    assert schedule_repo.count(Eq("plan_id", plan.id)) == 2


def test_schedule_repo_exists(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    schedule = plan.generate()
    schedule_repo.add(schedule)
    assert schedule_repo.exists(Eq("plan_id", plan.id)) is True
    assert schedule_repo.exists(Eq("plan_id", uuid7())) is False


def test_schedule_repo_load_plan_rel(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    schedule = plan.generate()
    schedule_repo.add(schedule)
    fetched = schedule_repo.get_by_id(schedule.id, Rel("plan"))
    assert fetched._plan is plan


def test_plan_repo_load_schedules_rel(schedule_repo, plan_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    plan = _make_plan(user.id)
    plan_repo.add(plan)
    s1 = plan.generate()
    s2 = plan.generate()
    schedule_repo.add(s1)
    schedule_repo.add(s2)
    fetched = plan_repo.get_by_id(plan.id, Rel("schedules"))
    assert len(fetched.schedules) == 2


# --- UserProfile repository tests ---


def test_profile_repo_add_and_get_by_id(profile_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    profile = Profile(user_id=user.id, display_name="Alice")
    profile_repo.add(profile)
    fetched = profile_repo.get_by_id(profile.id)
    assert fetched is profile


def test_profile_repo_get_by_id_returns_none(profile_repo):
    assert profile_repo.get_by_id(uuid7()) is None


def test_profile_repo_get_one_by_user_id(profile_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    profile = Profile(user_id=user.id, display_name="Alice")
    profile_repo.add(profile)
    fetched = profile_repo.get_one(Eq("user_id", user.id))
    assert fetched is profile


def test_profile_repo_get_one_or_none_returns_none(profile_repo):
    result = profile_repo.get_one_or_none(Eq("user_id", uuid7()))
    assert result is None


def test_profile_repo_update(profile_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    profile = Profile(user_id=user.id, display_name="Alice")
    profile_repo.add(profile)
    profile.display_name = "Alice Updated"
    updated = profile_repo.update(profile)
    assert updated.display_name == "Alice Updated"


def test_profile_repo_update_not_found(profile_repo):
    profile = Profile(user_id=uuid7())
    with pytest.raises(ProfileNotFoundError):
        profile_repo.update(profile)


def test_profile_repo_delete(profile_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    profile = Profile(user_id=user.id)
    profile_repo.add(profile)
    count = profile_repo.delete(Id(profile.id))
    assert count == 1
    assert profile_repo.get_by_id(profile.id) is None


def test_profile_repo_count(profile_repo, user_repo):
    u1 = User(email="a@b.com", name="A", password_hash="h")
    u2 = User(email="b@b.com", name="B", password_hash="h")
    user_repo.add(u1)
    user_repo.add(u2)
    profile_repo.add(Profile(user_id=u1.id))
    profile_repo.add(Profile(user_id=u2.id))
    assert profile_repo.count() == 2


def test_profile_repo_load_user_rel(profile_repo, user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    profile = Profile(user_id=user.id)
    profile_repo.add(profile)
    fetched = profile_repo.get_by_id(profile.id, Rel("user"))
    assert fetched._user is user


def test_user_repo_load_profile_rel(user_repo, profile_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    profile = Profile(user_id=user.id, display_name="A Display")
    profile_repo.add(profile)
    fetched = user_repo.get_by_id(user.id, Rel("profile"))
    assert fetched.profile is profile


def test_user_repo_load_profile_rel_none(user_repo):
    user = User(email="a@b.com", name="A", password_hash="h")
    user_repo.add(user)
    fetched = user_repo.get_by_id(user.id, Rel("profile"))
    assert fetched.profile is None
