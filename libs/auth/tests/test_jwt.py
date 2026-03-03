import uuid
from datetime import UTC, datetime, timedelta

import pytest
from amortsched.auth import JoseTokenService
from amortsched.core.errors import ExpiredTokenError, InvalidTokenError
from jose import jwt

SECRET = "test-secret-key-for-testing"


def test_create_and_decode_roundtrip():
    service = JoseTokenService(secret_key=SECRET)
    user_id = uuid.uuid4()
    token = service.create_access_token(user_id)
    decoded = service.decode_access_token(token)
    assert decoded == user_id


def test_decode_returns_uuid():
    service = JoseTokenService(secret_key=SECRET)
    user_id = uuid.uuid4()
    token = service.create_access_token(user_id)
    result = service.decode_access_token(token)
    assert isinstance(result, uuid.UUID)


def test_decode_invalid_token_raises():
    service = JoseTokenService(secret_key=SECRET)
    with pytest.raises(InvalidTokenError):
        service.decode_access_token("not-a-valid-jwt")


def test_decode_wrong_secret_raises():
    service = JoseTokenService(secret_key=SECRET)
    user_id = uuid.uuid4()
    token = service.create_access_token(user_id)

    other_service = JoseTokenService(secret_key="wrong-secret")
    with pytest.raises(InvalidTokenError):
        other_service.decode_access_token(token)


def test_decode_expired_token_raises():
    service = JoseTokenService(secret_key=SECRET, expire_minutes=0)
    user_id = uuid.uuid4()
    # Create a token that's already expired
    past = datetime.now(UTC) - timedelta(minutes=5)
    payload = {
        "sub": str(user_id),
        "iat": past,
        "exp": past + timedelta(seconds=1),
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    with pytest.raises(ExpiredTokenError):
        service.decode_access_token(token)


def test_decode_token_missing_sub_raises():
    payload = {
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    service = JoseTokenService(secret_key=SECRET)
    with pytest.raises(InvalidTokenError, match="missing subject"):
        service.decode_access_token(token)


def test_decode_token_invalid_uuid_sub_raises():
    payload = {
        "sub": "not-a-uuid",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    service = JoseTokenService(secret_key=SECRET)
    with pytest.raises(InvalidTokenError, match="Invalid subject"):
        service.decode_access_token(token)


def test_custom_algorithm():
    service = JoseTokenService(secret_key=SECRET, algorithm="HS384")
    user_id = uuid.uuid4()
    token = service.create_access_token(user_id)
    decoded = service.decode_access_token(token)
    assert decoded == user_id


def test_token_contains_expected_claims():
    service = JoseTokenService(secret_key=SECRET, expire_minutes=60)
    user_id = uuid.uuid4()
    token = service.create_access_token(user_id)
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert payload["sub"] == str(user_id)
    assert "iat" in payload
    assert "exp" in payload
