import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.add_one_time_extra_payment import (
    AddOneTimeExtraPaymentCommand,
    AddOneTimeExtraPaymentHandler,
)
from amortsched.core.entities import Plan, User
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return AddOneTimeExtraPaymentHandler(plan_repo)


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


def test_add_one_time_extra_payment(handler, sample_plan, sample_user):
    command = AddOneTimeExtraPaymentCommand(
        plan_id=sample_plan.id,
        user_id=sample_user.id,
        date=datetime.date(2025, 6, 15),
        amount=10_000,
    )
    plan = handler.handle(command)
    assert len(plan.one_time_extra_payments) == 1
    assert plan.one_time_extra_payments[0].amount == Decimal("10000")
