import datetime
from decimal import Decimal

import pytest
from amortsched.app.plans.generate_schedule import GenerateScheduleHandler, GenerateScheduleQuery
from amortsched.core.entities import Plan, User
from amortsched.core.values import OneTimeExtraPayment, PaymentKind, Term


@pytest.fixture
def handler(plan_repo):
    return GenerateScheduleHandler(plan_repo)


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


def test_generate_schedule(handler, sample_plan, sample_user):
    query = GenerateScheduleQuery(plan_id=sample_plan.id, user_id=sample_user.id)
    schedule = handler.handle(query)
    assert len(schedule.installments) > 0
    scheduled = [i for i in schedule.installments if i.payment.kind == PaymentKind.ScheduledPayment]
    assert len(scheduled) == 360  # 30 years * 12 months
    assert schedule.totals is not None
    assert schedule.totals.principal == pytest.approx(Decimal("300000"), rel=Decimal("0.01"))


def test_generate_schedule_with_extras(handler, sample_plan, sample_user, plan_repo):
    sample_plan.one_time_extra_payments.append(
        OneTimeExtraPayment(date=datetime.date(2025, 6, 15), amount=Decimal("50000"))
    )
    plan_repo.update(sample_plan)
    query = GenerateScheduleQuery(plan_id=sample_plan.id, user_id=sample_user.id)
    schedule = handler.handle(query)
    assert schedule.totals is not None
    assert schedule.totals.paid_off is True
    assert schedule.totals.months < 360
