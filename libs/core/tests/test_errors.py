from uuid import uuid7

from amortsched.core.errors import (
    DomainError,
    NotFoundError,
    PlanNotFoundError,
    UserNotFoundError,
    ValidationError,
)


def test_not_found_error_is_domain_error():
    assert issubclass(NotFoundError, DomainError)


def test_user_not_found_error_is_not_found_error():
    uid = uuid7()
    err = UserNotFoundError(uid)
    assert isinstance(err, NotFoundError)
    assert isinstance(err, DomainError)
    assert err.user_id == uid


def test_plan_not_found_error_is_not_found_error():
    pid = uuid7()
    err = PlanNotFoundError(pid)
    assert isinstance(err, NotFoundError)
    assert isinstance(err, DomainError)
    assert err.plan_id == pid


def test_validation_error_is_domain_error():
    errors = [{"field": "amount", "message": "required"}]
    err = ValidationError(errors)
    assert isinstance(err, DomainError)
    assert err.errors == errors
    assert str(err) == "Validation failed"


def test_validation_error_custom_message():
    err = ValidationError([], message="Bad input")
    assert str(err) == "Bad input"
    assert err.errors == []
