from amortsched.core.errors import (
    DomainError,
    ExpiredTokenError,
    InvalidTokenError,
)


def test_invalid_token_error_is_domain_error():
    err = InvalidTokenError()
    assert isinstance(err, DomainError)
    assert str(err) == "Invalid or malformed token"


def test_invalid_token_error_custom_message():
    err = InvalidTokenError("bad signature")
    assert str(err) == "bad signature"


def test_expired_token_error_is_invalid_token_error():
    err = ExpiredTokenError()
    assert isinstance(err, InvalidTokenError)
    assert str(err) == "Token has expired"
