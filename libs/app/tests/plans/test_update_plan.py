import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.update_plan import UpdatePlanCommand, UpdatePlanHandler
from amortsched.core.entities import Plan, User
from amortsched.core.values import InterestRateApplication, Term


@pytest.fixture
def handler(plan_repo):
    return UpdatePlanHandler(plan_repo)


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


def test_update_plan_partial(handler, sample_plan, sample_user):
    original_updated = sample_plan.updated_at
    command = UpdatePlanCommand(
        plan_id=sample_plan.id,
        user_id=sample_user.id,
        name="Renamed",
        amount=250_000,
    )
    updated = handler.handle(command)
    assert updated.name == "Renamed"
    assert updated.amount == Decimal("250000")
    assert updated.interest_rate == Decimal("5.5")
    assert updated.term == Term(30)
    assert updated.updated_at > original_updated


def test_update_plan_term_and_rate(handler, sample_plan, sample_user):
    command = UpdatePlanCommand(
        plan_id=sample_plan.id,
        user_id=sample_user.id,
        term=(15, 0),
        interest_rate=4.0,
        interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
    )
    updated = handler.handle(command)
    assert updated.term == Term(15)
    assert updated.interest_rate == Decimal("4.0")
    assert updated.interest_rate_application == InterestRateApplication.ProratedByPaymentPeriod
