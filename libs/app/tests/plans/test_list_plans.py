import datetime
import uuid
from decimal import Decimal

import pytest
from amortsched.app.plans.list_plans import ListPlansHandler, ListPlansQuery
from amortsched.core.entities import Plan, User
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return ListPlansHandler(plan_repo)


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


def test_list_plans(handler, sample_user, sample_plan):
    query = ListPlansQuery(user_id=sample_user.id)
    plans = handler.handle(query)
    assert len(plans) == 1
    assert plans[0].id == sample_plan.id


def test_list_plans_empty(handler):
    query = ListPlansQuery(user_id=uuid.uuid7())
    plans = handler.handle(query)
    assert plans == []
