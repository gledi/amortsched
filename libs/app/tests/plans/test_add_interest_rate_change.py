import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.add_interest_rate_change import (
    AddInterestRateChangeCommand,
    AddInterestRateChangeHandler,
)
from amortsched.core.entities import Plan, User
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return AddInterestRateChangeHandler(plan_repo)


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


def test_add_interest_rate_change(handler, sample_plan, sample_user):
    command = AddInterestRateChangeCommand(
        plan_id=sample_plan.id,
        user_id=sample_user.id,
        effective_date=datetime.date(2026, 1, 1),
        rate=6.0,
    )
    plan = handler.handle(command)
    assert len(plan.interest_rate_changes) == 1
    assert plan.interest_rate_changes[0].yearly_interest_rate == Decimal("6.0")
