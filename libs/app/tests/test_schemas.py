"""Tests for shared API schema types."""

import datetime
import uuid
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from amortsched.app.schemas import (
    AddExtraPaymentRequest,
    AddInterestRateChangeRequest,
    AddRecurringExtraPaymentRequest,
    AuthResponse,
    BalanceSchema,
    CreatePlanRequest,
    EarlyPaymentFeesSchema,
    InstallmentSchema,
    LoginRequest,
    PlanResponse,
    ProfileResponse,
    RegisterRequest,
    ScheduleResponse,
    TermSchema,
    TotalsSchema,
    UpdatePlanRequest,
    UpsertProfileRequest,
    UserResponse,
)

_UUID1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
_UUID2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
_DT = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
_DATE = datetime.date(2026, 1, 1)


def test_register_request_is_frozen():
    r = RegisterRequest(email="a@b.com", name="A", password="p")
    assert r.email == "a@b.com"
    with pytest.raises(FrozenInstanceError):
        r.email = "x"


def test_login_request_fields():
    r = LoginRequest(email="a@b.com", password="p")
    assert r.email == "a@b.com"
    assert r.password == "p"


def test_user_response_fields():
    u = UserResponse(id=_UUID1, email="a@b.com", name="A", is_active=True)
    assert u.id == _UUID1
    assert u.is_active is True


def test_auth_response_fields():
    user = UserResponse(id=_UUID1, email="a@b.com", name="A", is_active=True)
    a = AuthResponse(user=user, token="tok")
    assert a.token == "tok"


def test_upsert_profile_request_defaults():
    r = UpsertProfileRequest()
    assert r.display_name is None
    assert r.phone is None
    assert r.locale is None
    assert r.timezone is None


def test_profile_response_fields():
    p = ProfileResponse(
        id=_UUID1,
        user_id=_UUID2,
        display_name="D",
        phone=None,
        locale=None,
        timezone=None,
        created_at=_DT,
        updated_at=_DT,
    )
    assert p.user_id == _UUID2


def test_term_schema_defaults():
    t = TermSchema()
    assert t.years == 0
    assert t.months == 0


def test_early_payment_fees_schema_defaults():
    e = EarlyPaymentFeesSchema()
    assert e.fixed == Decimal("0.00")
    assert e.percent == Decimal("0.00")


def test_create_plan_request_fields():
    r = CreatePlanRequest(
        name="Test",
        amount=Decimal("100000.00"),
        interest_rate=Decimal("5.50"),
        term=TermSchema(years=30, months=0),
        start_date=_DATE,
    )
    assert r.name == "Test"
    assert r.interest_rate == Decimal("5.50")
    assert r.interest_rate_application == "whole_month"


def test_create_plan_request_start_date_default():
    r = CreatePlanRequest(
        name="Test",
        amount=Decimal("100000.00"),
        interest_rate=Decimal("5.50"),
        term=TermSchema(years=30),
    )
    assert r.start_date is None


def test_update_plan_request_all_none():
    r = UpdatePlanRequest()
    assert r.name is None
    assert r.amount is None


def test_add_extra_payment_request_fields():
    r = AddExtraPaymentRequest(date=_DATE, amount=Decimal("500.00"))
    assert r.date == _DATE


def test_add_recurring_extra_payment_request_fields():
    r = AddRecurringExtraPaymentRequest(start_date=_DATE, amount=Decimal("200.00"), count=12)
    assert r.count == 12


def test_add_interest_rate_change_request_fields():
    r = AddInterestRateChangeRequest(effective_date=datetime.date(2027, 1, 1), rate=Decimal("6.00"))
    assert r.rate == Decimal("6.00")


def test_plan_response_fields():
    p = PlanResponse(
        id=_UUID1,
        user_id=_UUID2,
        name="P",
        slug="p",
        amount=Decimal("100000.00"),
        interest_rate=Decimal("5.50"),
        term=TermSchema(years=30),
        start_date=_DATE,
        early_payment_fees=EarlyPaymentFeesSchema(),
        interest_rate_application="whole_month",
        status="draft",
        one_time_extra_payments=[],
        recurring_extra_payments=[],
        interest_rate_changes=[],
        created_at=_DT,
        updated_at=_DT,
    )
    assert p.status == "draft"


def test_balance_schema_fields():
    b = BalanceSchema(before=Decimal("100000.00"), after=Decimal("99500.00"))
    assert b.before == Decimal("100000.00")


def test_installment_schema_fields():
    i = InstallmentSchema(
        installment_number=1,
        year=2026,
        month=1,
        month_name="January",
        type="regular",
        principal=Decimal("300.00"),
        interest=Decimal("450.00"),
        fees=Decimal("0.00"),
        total=Decimal("750.00"),
        balance=BalanceSchema(before=Decimal("100000.00"), after=Decimal("99700.00")),
    )
    assert i.installment_number == 1


def test_totals_schema_fields():
    t = TotalsSchema(
        principal=Decimal("100000.00"),
        interest=Decimal("93000.00"),
        fees=Decimal("0.00"),
        total_outflow=Decimal("193000.00"),
        months=360,
        paid_off=True,
    )
    assert t.paid_off is True


def test_schedule_response_fields():
    s = ScheduleResponse(
        id=_UUID1,
        plan_id=_UUID2,
        installments=[],
        totals=None,
        generated_at=_DT,
    )
    assert s.plan_id == _UUID2


def test_all_schemas_are_frozen():
    """Every schema type must be frozen."""
    import dataclasses

    import amortsched.app.schemas as mod

    for name in dir(mod):
        cls = getattr(mod, name)
        if isinstance(cls, type) and dataclasses.is_dataclass(cls):
            assert cls.__dataclass_params__.frozen, f"{name} is not frozen"
