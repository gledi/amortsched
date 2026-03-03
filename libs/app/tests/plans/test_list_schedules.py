import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.list_schedules import ListSchedulesHandler, ListSchedulesQuery
from amortsched.core.entities import Plan, User
from amortsched.core.values import Term


@pytest.fixture
def handler(schedule_repo, plan_repo):
    return ListSchedulesHandler(schedule_repo, plan_repo)


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


def test_list_schedules(handler, sample_plan, sample_user, schedule_repo):
    schedule_repo.add(sample_plan.generate())
    schedule_repo.add(sample_plan.generate())
    query = ListSchedulesQuery(plan_id=sample_plan.id, user_id=sample_user.id)
    schedules = handler.handle(query)
    assert len(schedules) == 2


def test_list_schedules_empty(handler, sample_plan, sample_user):
    query = ListSchedulesQuery(plan_id=sample_plan.id, user_id=sample_user.id)
    schedules = handler.handle(query)
    assert schedules == []
