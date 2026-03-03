"""Tests for MashumaroValidator."""

import datetime
import uuid
from decimal import Decimal

import pytest
from amortsched.app.schemas import (
    AddExtraPaymentRequest,
    AddInterestRateChangeRequest,
    AddRecurringExtraPaymentRequest,
    AuthResponse,
    CreatePlanRequest,
    EarlyPaymentFeesSchema,
    LoginRequest,
    PlanResponse,
    ProfileResponse,
    RegisterRequest,
    ScheduleResponse,
    TermSchema,
    UpdatePlanRequest,
    UpsertProfileRequest,
    UserResponse,
)
from amortsched.core.errors import ValidationError
from amortsched.validators.vmashumaro import MashumaroValidator

_UUID1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
_UUID2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
_DT = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
_DATE = datetime.date(2026, 1, 1)


def test_register_request_round_trip():
    v = MashumaroValidator(RegisterRequest)
    data = {"email": "a@b.com", "name": "A", "password": "p"}
    obj = v.validate(data)
    assert isinstance(obj, RegisterRequest)
    assert obj.email == "a@b.com"
    result = v.serialize(obj)
    assert result["email"] == "a@b.com"


def test_login_request_round_trip():
    v = MashumaroValidator(LoginRequest)
    obj = v.validate({"email": "a@b.com", "password": "p"})
    assert obj.password == "p"


def test_user_response_camel_case():
    v = MashumaroValidator(UserResponse)
    obj = UserResponse(id=_UUID1, email="a@b.com", name="A", is_active=True)
    result = v.serialize(obj)
    assert "isActive" in result
    assert result["isActive"] is True
    assert isinstance(result["id"], str)


def test_auth_response_round_trip():
    v = MashumaroValidator(AuthResponse)
    data = {
        "user": {"id": str(_UUID1), "email": "a@b.com", "name": "A", "isActive": True},
        "token": "tok",
    }
    obj = v.validate(data)
    assert isinstance(obj, AuthResponse)
    assert isinstance(obj.user, UserResponse)
    assert obj.user.id == _UUID1
    result = v.serialize(obj)
    assert result["user"]["isActive"] is True


def test_upsert_profile_request_camel_input():
    v = MashumaroValidator(UpsertProfileRequest)
    obj = v.validate({"displayName": "DN", "phone": "123"})
    assert obj.display_name == "DN"


def test_profile_response_camel_output():
    v = MashumaroValidator(ProfileResponse)
    obj = ProfileResponse(
        id=_UUID1,
        user_id=_UUID2,
        display_name="D",
        phone=None,
        locale=None,
        timezone=None,
        created_at=_DT,
        updated_at=_DT,
    )
    result = v.serialize(obj)
    assert "userId" in result
    assert "displayName" in result
    assert "createdAt" in result


def test_create_plan_request_camel_input():
    v = MashumaroValidator(CreatePlanRequest)
    obj = v.validate(
        {
            "name": "Test",
            "amount": "100000.00",
            "interestRate": "5.50",
            "term": {"years": 30, "months": 0},
            "startDate": "2026-01-01",
        }
    )
    assert obj.interest_rate == Decimal("5.50")
    assert obj.amount == Decimal("100000.00")
    assert obj.start_date == _DATE
    assert obj.term.years == 30


def test_update_plan_request_partial():
    v = MashumaroValidator(UpdatePlanRequest)
    obj = v.validate({"name": "New Name"})
    assert obj.name == "New Name"
    assert obj.amount is None


def test_plan_response_camel_output():
    v = MashumaroValidator(PlanResponse)
    obj = PlanResponse(
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
    result = v.serialize(obj)
    assert "userId" in result
    assert "interestRate" in result
    assert "startDate" in result
    assert "earlyPaymentFees" in result
    assert isinstance(result["userId"], str)
    assert isinstance(result["amount"], str)


def test_schedule_response_camel_output():
    v = MashumaroValidator(ScheduleResponse)
    obj = ScheduleResponse(
        id=_UUID1,
        plan_id=_UUID2,
        installments=[],
        totals=None,
        generated_at=_DT,
    )
    result = v.serialize(obj)
    assert "planId" in result


def test_all_schema_types_can_be_validated():
    """Every shared schema type should be constructable via the validator."""
    all_types = [
        RegisterRequest,
        LoginRequest,
        UserResponse,
        AuthResponse,
        UpsertProfileRequest,
        ProfileResponse,
        CreatePlanRequest,
        UpdatePlanRequest,
        AddExtraPaymentRequest,
        AddRecurringExtraPaymentRequest,
        AddInterestRateChangeRequest,
        PlanResponse,
        ScheduleResponse,
    ]
    for t in all_types:
        v = MashumaroValidator(t)
        assert v._schema_type is t


def test_validate_raises_validation_error_on_bad_input():
    v = MashumaroValidator(RegisterRequest)
    with pytest.raises(ValidationError) as exc_info:
        v.validate({"bad_field": "nope"})
    assert len(exc_info.value.errors) > 0
