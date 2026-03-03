import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.save_schedule import SaveScheduleCommand, SaveScheduleHandler
from amortsched.core.entities import Plan, User
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo, schedule_repo):
    return SaveScheduleHandler(plan_repo, schedule_repo)


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


def test_save_schedule_persists(handler, sample_plan, sample_user, schedule_repo):
    command = SaveScheduleCommand(plan_id=sample_plan.id, user_id=sample_user.id)
    schedule = handler.handle(command)
    assert schedule.plan_id == sample_plan.id
    assert len(schedule.installments) > 0
    assert schedule.totals is not None
    fetched = schedule_repo.get_by_id(schedule.id)
    assert fetched is schedule


def test_save_schedule_multiple_creates_separate(handler, sample_plan, sample_user, schedule_repo):
    cmd = SaveScheduleCommand(plan_id=sample_plan.id, user_id=sample_user.id)
    s1 = handler.handle(cmd)
    s2 = handler.handle(cmd)
    assert s1.id != s2.id
    assert schedule_repo.count() == 2
