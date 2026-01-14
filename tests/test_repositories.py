import datetime
from decimal import Decimal
from uuid import UUID, uuid7

import pytest

from amortsched.amortization import Term
from amortsched.entities import Plan, User
from amortsched.errors import DuplicateEmailError, PlanNotFoundError, UserNotFoundError

_FAKE_USER_ID_1 = UUID("01945b88-4f4a-7000-8000-000000000001")
_FAKE_USER_ID_2 = UUID("01945b88-4f4a-7000-8000-000000000002")
_FAKE_USER_ID_3 = UUID("01945b88-4f4a-7000-8000-000000000003")


class TestUserRepository:
    def test_add_and_get_by_id(self, user_repo):
        user = User(email="a@b.com", name="A B", password_hash="hashed")
        user_repo.add(user)
        fetched = user_repo.get_by_id(user.id)
        assert fetched is user

    def test_get_by_email(self, user_repo):
        user = User(email="a@b.com", name="A B", password_hash="hashed")
        user_repo.add(user)
        fetched = user_repo.get_by_email("a@b.com")
        assert fetched is user

    def test_duplicate_email_raises(self, user_repo):
        user1 = User(email="a@b.com", name="A", password_hash="hashed")
        user2 = User(email="a@b.com", name="B", password_hash="hashed2")
        user_repo.add(user1)
        with pytest.raises(DuplicateEmailError) as exc_info:
            user_repo.add(user2)
        assert exc_info.value.email == "a@b.com"

    def test_get_by_id_not_found_raises(self, user_repo):
        missing_id = uuid7()
        with pytest.raises(UserNotFoundError) as exc_info:
            user_repo.get_by_id(missing_id)
        assert exc_info.value.user_id == missing_id

    def test_get_by_email_not_found_raises(self, user_repo):
        with pytest.raises(UserNotFoundError):
            user_repo.get_by_email("missing@example.com")

    def test_remove(self, user_repo):
        user = User(email="a@b.com", name="A B", password_hash="hashed")
        user_repo.add(user)
        user_repo.remove(user.id)
        with pytest.raises(UserNotFoundError):
            user_repo.get_by_id(user.id)
        with pytest.raises(UserNotFoundError):
            user_repo.get_by_email("a@b.com")

    def test_list_all(self, user_repo):
        user1 = User(email="a@b.com", name="A", password_hash="hashed")
        user2 = User(email="c@d.com", name="C", password_hash="hashed")
        user_repo.add(user1)
        user_repo.add(user2)
        all_users = user_repo.list_all()
        assert len(all_users) == 2
        assert set(u.id for u in all_users) == {user1.id, user2.id}


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


class TestPlanRepository:
    def test_add_and_get_by_id(self, plan_repo):
        plan = _make_plan(_FAKE_USER_ID_1)
        plan_repo.add(plan)
        fetched = plan_repo.get_by_id(plan.id)
        assert fetched is plan

    def test_get_by_id_not_found_raises(self, plan_repo):
        missing_id = uuid7()
        with pytest.raises(PlanNotFoundError) as exc_info:
            plan_repo.get_by_id(missing_id)
        assert exc_info.value.plan_id == missing_id

    def test_update(self, plan_repo):
        plan = _make_plan(_FAKE_USER_ID_1)
        plan_repo.add(plan)
        plan.name = "Updated"
        plan_repo.update(plan)
        fetched = plan_repo.get_by_id(plan.id)
        assert fetched.name == "Updated"

    def test_update_not_found_raises(self, plan_repo):
        plan = _make_plan(_FAKE_USER_ID_1)
        with pytest.raises(PlanNotFoundError):
            plan_repo.update(plan)

    def test_remove(self, plan_repo):
        plan = _make_plan(_FAKE_USER_ID_1)
        plan_repo.add(plan)
        plan_repo.remove(plan.id)
        with pytest.raises(PlanNotFoundError):
            plan_repo.get_by_id(plan.id)

    def test_remove_not_found_raises(self, plan_repo):
        with pytest.raises(PlanNotFoundError):
            plan_repo.remove(uuid7())

    def test_list_by_user(self, plan_repo):
        plan1 = _make_plan(_FAKE_USER_ID_1, "Plan A")
        plan2 = _make_plan(_FAKE_USER_ID_1, "Plan B")
        plan3 = _make_plan(_FAKE_USER_ID_2, "Plan C")
        plan_repo.add(plan1)
        plan_repo.add(plan2)
        plan_repo.add(plan3)

        u1_plans = plan_repo.list_by_user(_FAKE_USER_ID_1)
        assert len(u1_plans) == 2
        assert all(p.user_id == _FAKE_USER_ID_1 for p in u1_plans)

        u2_plans = plan_repo.list_by_user(_FAKE_USER_ID_2)
        assert len(u2_plans) == 1
        assert u2_plans[0].name == "Plan C"

        assert plan_repo.list_by_user(_FAKE_USER_ID_3) == []
