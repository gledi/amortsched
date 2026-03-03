import datetime
import uuid
from decimal import Decimal

import pytest
from amortsched.app.plans.get_plan import GetPlanHandler, GetPlanQuery
from amortsched.core.entities import Plan, User
from amortsched.core.errors import PlanNotFoundError, PlanOwnershipError
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return GetPlanHandler(plan_repo)


@pytest.fixture
def sample_user(user_repo):
    user = User(email="alice@example.com", name="Alice", password_hash="hashed")
    user_repo.add(user)
    return user


@pytest.fixture
def sample_plan(plan_repo, sample_user):
    plan = Plan(
        user_id=sample_user.id,
        name="Home Loan",
        slug="home-loan",
        amount=Decimal("300000"),
        term=Term(30),
        interest_rate=Decimal("5.5"),
        start_date=datetime.date(2025, 1, 1),
    )
    plan_repo.add(plan)
    return plan


def test_get_plan_with_ownership(handler, sample_plan, sample_user):
    query = GetPlanQuery(plan_id=sample_plan.id, user_id=sample_user.id)
    fetched = handler.handle(query)
    assert fetched.id == sample_plan.id


def test_get_plan_wrong_owner(handler, sample_plan):
    other_user_id = uuid.uuid7()
    query = GetPlanQuery(plan_id=sample_plan.id, user_id=other_user_id)
    with pytest.raises(PlanOwnershipError) as exc:
        handler.handle(query)
    assert exc.value.plan_id == sample_plan.id
    assert exc.value.user_id == other_user_id


def test_get_plan_not_found(handler, sample_user):
    query = GetPlanQuery(plan_id=uuid.uuid7(), user_id=sample_user.id)
    with pytest.raises(PlanNotFoundError):
        handler.handle(query)
