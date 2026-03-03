import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.save_plan import SavePlanCommand, SavePlanHandler
from amortsched.core.entities import Plan, User
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return SavePlanHandler(plan_repo)


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


def test_save_plan_transitions_to_saved(handler, sample_plan, sample_user):
    assert sample_plan.status == Plan.Status.Draft
    command = SavePlanCommand(plan_id=sample_plan.id, user_id=sample_user.id)
    saved = handler.handle(command)
    assert saved.status == Plan.Status.Saved
