import datetime
import uuid
from decimal import Decimal

import pytest
from amortsched.app.plans.delete_schedule import DeleteScheduleCommand, DeleteScheduleHandler
from amortsched.core.entities import Plan, User
from amortsched.core.errors import PlanOwnershipError, ScheduleNotFoundError
from amortsched.core.values import Term


@pytest.fixture
def handler(schedule_repo, plan_repo):
    return DeleteScheduleHandler(schedule_repo, plan_repo)


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


@pytest.fixture
def saved_schedule(sample_plan, schedule_repo):
    schedule = sample_plan.generate()
    schedule_repo.add(schedule)
    return schedule


def test_delete_schedule(handler, saved_schedule, sample_user, schedule_repo):
    command = DeleteScheduleCommand(schedule_id=saved_schedule.id, user_id=sample_user.id)
    handler.handle(command)
    assert schedule_repo.get_by_id(saved_schedule.id) is None


def test_delete_schedule_not_found(handler, sample_user):
    command = DeleteScheduleCommand(schedule_id=uuid.uuid7(), user_id=sample_user.id)
    with pytest.raises(ScheduleNotFoundError):
        handler.handle(command)


def test_delete_schedule_wrong_owner(handler, saved_schedule):
    command = DeleteScheduleCommand(schedule_id=saved_schedule.id, user_id=uuid.uuid7())
    with pytest.raises(PlanOwnershipError):
        handler.handle(command)
