import datetime
from decimal import Decimal
from uuid import uuid7

import pytest

from amortsched.amortization import InterestRateApplication, PaymentKind, Term
from amortsched.entities import Plan
from amortsched.errors import AuthenticationError, PlanNotFoundError, PlanOwnershipError, UserNotFoundError


class TestUserService:
    def test_register(self, user_service, password_hasher):
        user = user_service.register(email="bob@example.com", name="Bob", password="pw123")
        assert user.email == "bob@example.com"
        assert user.name == "Bob"
        assert password_hasher.verify("pw123", user.password_hash)

    def test_authenticate_success(self, user_service):
        user_service.register(email="bob@example.com", name="Bob", password="pw123")
        user = user_service.authenticate(email="bob@example.com", password="pw123")
        assert user.email == "bob@example.com"

    def test_authenticate_wrong_password(self, user_service):
        user_service.register(email="bob@example.com", name="Bob", password="pw123")
        with pytest.raises(AuthenticationError):
            user_service.authenticate(email="bob@example.com", password="wrong")

    def test_authenticate_unknown_email(self, user_service):
        with pytest.raises(AuthenticationError):
            user_service.authenticate(email="nobody@example.com", password="pw")

    def test_get_user(self, user_service, sample_user):
        fetched = user_service.get_user(sample_user.id)
        assert fetched.email == sample_user.email

    def test_get_user_not_found(self, user_service):
        with pytest.raises(UserNotFoundError):
            user_service.get_user(uuid7())


class TestPlanService:
    def test_create_plan(self, plan_service, sample_user):
        plan = plan_service.create_plan(
            user_id=sample_user.id,
            name="My Plan",
            amount=100_000,
            term=15,
            interest_rate=4.5,
            start_date=datetime.date(2025, 6, 1),
        )
        assert plan.name == "My Plan"
        assert plan.amount == Decimal("100000")
        assert plan.term == Term(15)
        assert plan.interest_rate == Decimal("4.5")
        assert plan.status == Plan.Status.Draft

    def test_create_plan_with_tuple_term(self, plan_service, sample_user):
        plan = plan_service.create_plan(
            user_id=sample_user.id,
            name="Short",
            amount=50_000,
            term=(2, 6),
            interest_rate=3.0,
            start_date=datetime.date(2025, 1, 1),
        )
        assert plan.term == Term(2, 6)
        assert plan.term.periods == 30

    def test_get_plan_with_ownership(self, plan_service, sample_plan, sample_user):
        fetched = plan_service.get_plan(sample_plan.id, sample_user.id)
        assert fetched.id == sample_plan.id

    def test_get_plan_wrong_owner(self, plan_service, sample_plan):
        other_user_id = uuid7()
        with pytest.raises(PlanOwnershipError) as exc:
            plan_service.get_plan(sample_plan.id, other_user_id)
        assert exc.value.plan_id == sample_plan.id
        assert exc.value.user_id == other_user_id

    def test_get_plan_not_found(self, plan_service, sample_user):
        with pytest.raises(PlanNotFoundError):
            plan_service.get_plan(uuid7(), sample_user.id)

    def test_list_plans(self, plan_service, sample_user, sample_plan):
        plans = plan_service.list_plans(sample_user.id)
        assert len(plans) == 1
        assert plans[0].id == sample_plan.id

    def test_list_plans_empty(self, plan_service):
        assert plan_service.list_plans(uuid7()) == []

    def test_update_plan_partial(self, plan_service, sample_plan, sample_user):
        original_updated = sample_plan.updated_at
        updated = plan_service.update_plan(
            sample_plan.id,
            sample_user.id,
            name="Renamed",
            amount=250_000,
        )
        assert updated.name == "Renamed"
        assert updated.amount == Decimal("250000")
        # Unchanged fields preserved
        assert updated.interest_rate == Decimal("5.5")
        assert updated.term == Term(30)
        assert updated.updated_at > original_updated

    def test_update_plan_term_and_rate(self, plan_service, sample_plan, sample_user):
        updated = plan_service.update_plan(
            sample_plan.id,
            sample_user.id,
            term=(15, 0),
            interest_rate=4.0,
            interest_rate_application=InterestRateApplication.ProratedByPaymentPeriod,
        )
        assert updated.term == Term(15)
        assert updated.interest_rate == Decimal("4.0")
        assert updated.interest_rate_application == InterestRateApplication.ProratedByPaymentPeriod

    def test_add_one_time_extra_payment(self, plan_service, sample_plan, sample_user):
        plan = plan_service.add_one_time_extra_payment(
            sample_plan.id, sample_user.id, datetime.date(2025, 6, 15), 10_000
        )
        assert len(plan.one_time_extra_payments) == 1
        assert plan.one_time_extra_payments[0].amount == Decimal("10000")

    def test_add_recurring_extra_payment(self, plan_service, sample_plan, sample_user):
        plan = plan_service.add_recurring_extra_payment(
            sample_plan.id, sample_user.id, datetime.date(2025, 2, 1), 500, 12
        )
        assert len(plan.recurring_extra_payments) == 1
        assert plan.recurring_extra_payments[0].count == 12

    def test_add_interest_rate_change(self, plan_service, sample_plan, sample_user):
        plan = plan_service.add_interest_rate_change(sample_plan.id, sample_user.id, datetime.date(2026, 1, 1), 6.0)
        assert len(plan.interest_rate_changes) == 1
        assert plan.interest_rate_changes[0].yearly_interest_rate == Decimal("6.0")

    def test_save_plan(self, plan_service, sample_plan, sample_user):
        assert sample_plan.status == Plan.Status.Draft
        saved = plan_service.save_plan(sample_plan.id, sample_user.id)
        assert saved.status == Plan.Status.Saved

    def test_delete_plan(self, plan_service, sample_plan, sample_user):
        plan_service.delete_plan(sample_plan.id, sample_user.id)
        with pytest.raises(PlanNotFoundError):
            plan_service.get_plan(sample_plan.id, sample_user.id)

    def test_delete_plan_wrong_owner(self, plan_service, sample_plan):
        with pytest.raises(PlanOwnershipError):
            plan_service.delete_plan(sample_plan.id, uuid7())

    def test_generate_schedule(self, plan_service, sample_plan, sample_user):
        installments, totals = plan_service.generate_schedule(sample_plan.id, sample_user.id)
        assert len(installments) > 0
        scheduled = [i for i in installments if i.payment.kind == PaymentKind.ScheduledPayment]
        assert len(scheduled) == 360  # 30 years * 12 months
        assert totals is not None
        assert totals.principal == pytest.approx(Decimal("300000"), rel=Decimal("0.01"))

    def test_generate_schedule_with_extras(self, plan_service, sample_plan, sample_user):
        plan_service.add_one_time_extra_payment(sample_plan.id, sample_user.id, datetime.date(2025, 6, 15), 50_000)
        installments, totals = plan_service.generate_schedule(sample_plan.id, sample_user.id)
        assert totals is not None
        assert totals.paid_off is True
        # Should finish earlier than 360 months
        assert totals.months < 360
