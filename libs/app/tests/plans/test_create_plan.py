import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.create_plan import CreatePlanCommand, CreatePlanHandler
from amortsched.core.entities import Plan
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return CreatePlanHandler(plan_repo)


@pytest.fixture
def sample_user(user_repo):
    from amortsched.core.entities import User

    user = User(email="alice@example.com", name="Alice", password_hash="hashed")
    user_repo.add(user)
    return user


def test_create_plan(handler, sample_user):
    command = CreatePlanCommand(
        user_id=sample_user.id,
        name="My Plan",
        amount=100_000,
        term=15,
        interest_rate=4.5,
        start_date=datetime.date(2025, 6, 1),
    )
    plan = handler.handle(command)
    assert plan.name == "My Plan"
    assert plan.amount == Decimal("100000")
    assert plan.term == Term(15)
    assert plan.interest_rate == Decimal("4.5")
    assert plan.status == Plan.Status.Draft


def test_create_plan_with_tuple_term(handler, sample_user):
    command = CreatePlanCommand(
        user_id=sample_user.id,
        name="Short",
        amount=50_000,
        term=(2, 6),
        interest_rate=3.0,
        start_date=datetime.date(2025, 1, 1),
    )
    plan = handler.handle(command)
    assert plan.term == Term(2, 6)
    assert plan.term.periods == 30


def test_create_plan_generates_slug(handler, sample_user):
    command = CreatePlanCommand(
        user_id=sample_user.id,
        name="Home Loan",
        amount=300_000,
        term=30,
        interest_rate=5.5,
        start_date=datetime.date(2025, 1, 1),
    )
    plan = handler.handle(command)
    assert plan.slug == "home-loan"


def test_create_plan_persists(handler, sample_user, plan_repo):
    command = CreatePlanCommand(
        user_id=sample_user.id,
        name="Test",
        amount=100_000,
        term=10,
        interest_rate=5.0,
        start_date=datetime.date(2025, 1, 1),
    )
    plan = handler.handle(command)
    fetched = plan_repo.get_by_id(plan.id)
    assert fetched is plan
