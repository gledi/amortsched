import datetime
import uuid
from decimal import Decimal

import pytest
from amortsched.app.plans.delete_plan import DeletePlanCommand, DeletePlanHandler
from amortsched.core.entities import Plan, User
from amortsched.core.errors import PlanOwnershipError
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return DeletePlanHandler(plan_repo)


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


def test_delete_plan(handler, sample_plan, sample_user, plan_repo):
    command = DeletePlanCommand(plan_id=sample_plan.id, user_id=sample_user.id)
    handler.handle(command)
    assert plan_repo.get_by_id(sample_plan.id) is None


def test_delete_plan_wrong_owner(handler, sample_plan):
    command = DeletePlanCommand(plan_id=sample_plan.id, user_id=uuid.uuid7())
    with pytest.raises(PlanOwnershipError):
        handler.handle(command)
