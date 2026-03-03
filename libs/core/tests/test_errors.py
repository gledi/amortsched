from uuid import uuid7

from amortsched.core.errors import (
    DomainError,
    NotFoundError,
    PlanNotFoundError,
    UserNotFoundError,
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
