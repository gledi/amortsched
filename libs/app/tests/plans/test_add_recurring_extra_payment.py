import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.add_recurring_extra_payment import (
    AddRecurringExtraPaymentCommand,
    AddRecurringExtraPaymentHandler,
)
from amortsched.core.entities import Plan, User
from amortsched.core.values import Term


@pytest.fixture
def handler(plan_repo):
    return AddRecurringExtraPaymentHandler(plan_repo)


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


def test_add_recurring_extra_payment(handler, sample_plan, sample_user):
    command = AddRecurringExtraPaymentCommand(
        plan_id=sample_plan.id,
        user_id=sample_user.id,
        start_date=datetime.date(2025, 2, 1),
        amount=500,
        count=12,
    )
    plan = handler.handle(command)
    assert len(plan.recurring_extra_payments) == 1
    assert plan.recurring_extra_payments[0].count == 12
