import datetime
import time
from decimal import Decimal
from uuid import UUID

from amortsched.amortization import (
    AmortizationSchedule,
    InterestRateApplication,
    InterestRateChange,
    OneTimeExtraPayment,
    PaymentKind,
    RecurringExtraPayment,
    Term,
)
from amortsched.entities import Plan, User

_FAKE_USER_ID = UUID("01945b88-4f4a-7000-8000-000000000001")


class TestUser:
    def test_repr_does_not_leak_password(self):
        user = User(email="dan@example.com", name="Dan", password_hash="hashed-value")
        r = repr(user)
        assert "hashed-value" not in r
        assert "password_hash" not in r

    def test_created_at_is_set(self):
        user = User(email="eve@example.com", name="Eve")
        assert isinstance(user.created_at, datetime.datetime)
        assert user.created_at.tzinfo is datetime.UTC


class TestPlan:
    def test_defaults(self):
        plan = Plan(
            user_id=_FAKE_USER_ID,
            name="Test",
            slug="test",
            amount=Decimal("1000"),
            term=Term(1),
            interest_rate=Decimal("10"),
            start_date=datetime.date(2025, 1, 1),
        )
        assert plan.status == Plan.Status.Draft
        assert plan.one_time_extra_payments == []
        assert plan.recurring_extra_payments == []
        assert plan.interest_rate_changes == []
        assert plan.interest_rate_application == InterestRateApplication.WholeMonth

    def test_to_schedule_round_trip(self):
        plan = Plan(
            user_id=_FAKE_USER_ID,
            name="Test",
            slug="test",
            amount=Decimal("1000"),
            term=Term(1),
            interest_rate=Decimal("10"),
            start_date=datetime.date(2025, 1, 1),
            one_time_extra_payments=[OneTimeExtraPayment(date=datetime.date(2025, 3, 15), amount=Decimal("200"))],
            recurring_extra_payments=[
                RecurringExtraPayment(start_date=datetime.date(2025, 2, 1), amount=Decimal("50"), count=3)
            ],
            interest_rate_changes=[
                InterestRateChange(effective_date=datetime.date(2025, 6, 1), yearly_interest_rate=Decimal("12"))
            ],
        )
        schedule = plan.to_schedule()
        assert isinstance(schedule, AmortizationSchedule)
        assert schedule.amount == Decimal("1000")
        assert schedule.interest_rate == Decimal("10")
        assert schedule.term == Term(1)
        assert len(schedule.one_time_extra_payments) == 1
        assert len(schedule.recurring_extra_payments) == 1
        assert len(schedule.interest_rate_changes) == 1

    def test_generate_produces_installments(self):
        plan = Plan(
            user_id=_FAKE_USER_ID,
            name="Test",
            slug="test",
            amount=Decimal("1000"),
            term=Term(1),
            interest_rate=Decimal("10"),
            start_date=datetime.date(2025, 1, 1),
        )
        installments = plan.generate()
        assert len(installments) > 0
        scheduled = [i for i in installments if i.payment.kind == PaymentKind.ScheduledPayment]
        assert len(scheduled) == 12

    def test_touch_updates_timestamp(self):
        plan = Plan(
            user_id=_FAKE_USER_ID,
            name="Test",
            slug="test",
            amount=Decimal("1000"),
            term=Term(1),
            interest_rate=Decimal("10"),
            start_date=datetime.date(2025, 1, 1),
        )
        original = plan.updated_at
        time.sleep(0.01)
        plan.touch()
        assert plan.updated_at > original
