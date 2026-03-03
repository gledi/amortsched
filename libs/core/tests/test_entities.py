import datetime
import time
import uuid
from decimal import Decimal
from uuid import UUID, uuid7

import pytest
from amortsched.core.amortization import AmortizationSchedule
from amortsched.core.entities import Plan, Profile, Schedule, User
from amortsched.core.errors import (
    DuplicatePlanError,
    DuplicateProfileError,
    PlanAssociationError,
    ProfileAssociationError,
    ScheduleAssociationError,
    UnboundPlanError,
    UnboundProfileError,
    UnboundScheduleError,
    UserAssociationError,
)
from amortsched.core.values import (
    InterestRateApplication,
    InterestRateChange,
    OneTimeExtraPayment,
    PaymentKind,
    RecurringExtraPayment,
    Term,
)

_FAKE_USER_ID = UUID("01945b88-4f4a-7000-8000-000000000001")
_FAKE_USER_ID_2 = UUID("01945b88-4f4a-7000-8000-000000000002")


def _make_user(user_id: UUID = _FAKE_USER_ID) -> User:
    return User(id=user_id, email="dan@example.com", name="Dan", password_hash="hashed")


def _make_plan(user_id: UUID = _FAKE_USER_ID) -> Plan:
    return Plan(
        user_id=user_id,
        name="Test",
        slug="test",
        amount=Decimal("1000"),
        term=Term(1),
        interest_rate=Decimal("10"),
        start_date=datetime.date(2025, 1, 1),
    )


def test_user_repr_does_not_leak_password():
    user = User(email="dan@example.com", name="Dan", password_hash="hashed-value")
    r = repr(user)
    assert "hashed-value" not in r
    assert "password_hash" not in r


def test_user_created_at_is_set():
    user = User(email="eve@example.com", name="Eve")
    assert isinstance(user.created_at, datetime.datetime)
    assert user.created_at.tzinfo is datetime.UTC


def test_user_revision_starts_at_zero():
    user = _make_user()
    assert user._revision == 0


def test_user_plans_property_returns_empty_list():
    user = _make_user()
    assert user.plans == []


def test_user_plans_setter_loads_without_validation():
    user = _make_user()
    plan = _make_plan(user_id=uuid7())  # mismatched user_id on purpose
    user.plans = [plan]
    assert user.plans == [plan]


def test_user_add_plan_valid():
    user = _make_user()
    plan = _make_plan(user_id=user.id)
    user.add_plan(plan)
    assert len(user.plans) == 1
    assert plan.user is user


def test_user_add_plan_mismatched_user_id_raises():
    user = _make_user()
    plan = _make_plan(user_id=_FAKE_USER_ID_2)
    with pytest.raises(PlanAssociationError) as exc_info:
        user.add_plan(plan)
    assert exc_info.value.plan_id == plan.id
    assert exc_info.value.expected_user_id == _FAKE_USER_ID_2
    assert exc_info.value.actual_user_id == user.id


def test_user_add_plan_duplicate_raises():
    user = _make_user()
    plan = _make_plan(user_id=user.id)
    user.add_plan(plan)
    with pytest.raises(DuplicatePlanError) as exc_info:
        user.add_plan(plan)
    assert exc_info.value.plan_id == plan.id
    assert exc_info.value.user_id == user.id


def test_user_add_plans_multiple():
    user = _make_user()
    plan1 = _make_plan(user_id=user.id)
    plan2 = Plan(
        user_id=user.id,
        name="Second",
        slug="second",
        amount=Decimal("2000"),
        term=Term(2),
        interest_rate=Decimal("5"),
        start_date=datetime.date(2025, 6, 1),
    )
    user.add_plans([plan1, plan2])
    assert len(user.plans) == 2


def test_user_touch_updates_timestamp():
    user = _make_user()
    original = user.updated_at
    time.sleep(0.01)
    user.touch()
    assert user.updated_at > original


def test_plan_defaults():
    plan = _make_plan()
    assert plan.status == Plan.Status.Draft
    assert plan.one_time_extra_payments == []
    assert plan.recurring_extra_payments == []
    assert plan.interest_rate_changes == []
    assert plan.interest_rate_application == InterestRateApplication.WholeMonth


def test_plan_revision_starts_at_zero():
    plan = _make_plan()
    assert plan._revision == 0


def test_plan_user_property_raises_when_unbound():
    plan = _make_plan()
    with pytest.raises(UnboundPlanError) as exc_info:
        _ = plan.user
    assert exc_info.value.plan_id == plan.id


def test_plan_user_setter_loads_without_validation():
    plan = _make_plan()
    user = _make_user(user_id=uuid7())  # mismatched on purpose
    plan.user = user
    assert plan.user is user


def test_plan_add_user_valid():
    plan = _make_plan()
    user = _make_user()
    plan.add_user(user)
    assert plan.user is user


def test_plan_add_user_mismatched_raises():
    plan = _make_plan()
    other_user = _make_user(user_id=_FAKE_USER_ID_2)
    with pytest.raises(UserAssociationError) as exc_info:
        plan.add_user(other_user)
    assert exc_info.value.plan_id == plan.id
    assert exc_info.value.plan_user_id == _FAKE_USER_ID
    assert exc_info.value.user_id == _FAKE_USER_ID_2


def test_plan_to_schedule_round_trip():
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


def test_plan_generate_returns_schedule_entity():
    plan = _make_plan()
    result = plan.generate()
    assert isinstance(result, Schedule)
    assert result.plan_id == plan.id
    assert len(result.installments) > 0
    scheduled = [i for i in result.installments if i.payment.kind == PaymentKind.ScheduledPayment]
    assert len(scheduled) == 12


def test_plan_generate_schedule_has_totals():
    plan = _make_plan()
    result = plan.generate()
    assert result.totals is not None
    assert result.totals.months == 12


def test_plan_touch_updates_timestamp():
    plan = _make_plan()
    original = plan.updated_at
    time.sleep(0.01)
    plan.touch()
    assert plan.updated_at > original


def test_schedule_revision_starts_at_zero():
    plan = _make_plan()
    schedule = plan.generate()
    assert schedule._revision == 0


def test_schedule_plan_id_matches():
    plan = _make_plan()
    schedule = plan.generate()
    assert schedule.plan_id == plan.id


def test_schedule_generated_at_is_set():
    plan = _make_plan()
    schedule = plan.generate()
    assert isinstance(schedule.generated_at, datetime.datetime)
    assert schedule.generated_at.tzinfo is datetime.UTC


# --- Plan._schedules tests ---


def test_plan_schedules_property_returns_empty_list():
    plan = _make_plan()
    assert plan.schedules == []


def test_plan_schedules_setter_loads_without_validation():
    plan = _make_plan()
    schedule = Schedule(plan_id=uuid7(), installments=[], totals=None)  # mismatched plan_id on purpose
    plan.schedules = [schedule]
    assert plan.schedules == [schedule]


def test_plan_add_schedule_valid():
    plan = _make_plan()
    schedule = plan.generate()
    plan.add_schedule(schedule)
    assert len(plan.schedules) == 1
    assert plan.schedules[0] is schedule


def test_plan_add_schedule_sets_back_reference():
    plan = _make_plan()
    schedule = plan.generate()
    plan.add_schedule(schedule)
    assert schedule.plan is plan


def test_plan_add_schedule_mismatched_plan_id_raises():
    plan = _make_plan()
    other_plan = _make_plan(user_id=_FAKE_USER_ID_2)
    schedule = other_plan.generate()
    with pytest.raises(ScheduleAssociationError) as exc_info:
        plan.add_schedule(schedule)
    assert exc_info.value.schedule_id == schedule.id
    assert exc_info.value.expected_plan_id == schedule.plan_id
    assert exc_info.value.actual_plan_id == plan.id


# --- Schedule._plan tests ---


def test_schedule_plan_property_raises_when_unbound():
    plan = _make_plan()
    schedule = plan.generate()
    with pytest.raises(UnboundScheduleError) as exc_info:
        _ = schedule.plan
    assert exc_info.value.schedule_id == schedule.id


def test_schedule_plan_setter_loads_without_validation():
    plan = _make_plan()
    schedule = Schedule(plan_id=uuid7(), installments=[], totals=None)  # mismatched on purpose
    schedule.plan = plan
    assert schedule.plan is plan


# --- UserProfile tests ---


def test_user_profile_defaults():
    uid = uuid.uuid7()
    profile = Profile(user_id=uid)
    assert profile.user_id == uid
    assert profile.display_name is None
    assert profile.phone is None
    assert profile.locale is None
    assert profile.timezone is None


def test_user_profile_unbound_raises():
    profile = Profile(user_id=uuid.uuid7())
    with pytest.raises(UnboundProfileError):
        _ = profile.user


def test_user_set_profile():
    user = User(email="alice@example.com", name="Alice")
    profile = Profile(user_id=user.id, display_name="Alice W.")
    user.add_profile(profile)
    assert user.profile is profile
    assert profile._user is user


def test_user_set_profile_wrong_user_raises():
    user = User(email="alice@example.com", name="Alice")
    profile = Profile(user_id=uuid.uuid7())
    with pytest.raises(ProfileAssociationError):
        user.add_profile(profile)


def test_user_set_profile_duplicate_raises():
    user = User(email="alice@example.com", name="Alice")
    profile1 = Profile(user_id=user.id)
    profile2 = Profile(user_id=user.id)
    user.add_profile(profile1)
    with pytest.raises(DuplicateProfileError):
        user.add_profile(profile2)


def test_user_profile_touch():
    profile = Profile(user_id=uuid.uuid7())
    old_updated = profile.updated_at
    profile.touch()
    assert profile.updated_at >= old_updated
