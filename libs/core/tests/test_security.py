import pytest
from amortsched.core.security import PBKDF2PasswordHasher, ScryptPasswordHasher


@pytest.fixture(
    params=[PBKDF2PasswordHasher, ScryptPasswordHasher],
    ids=["pbkdf2", "scrypt"],
)
def hasher(request):
    return request.param()


def test_hash_returns_non_empty_string(hasher):
    result = hasher.hash("password123")
    assert isinstance(result, str)
    assert len(result) > 0


def test_verify_correct_password(hasher):
    hashed = hasher.hash("correct-horse-battery-staple")
    assert hasher.verify("correct-horse-battery-staple", hashed) is True


def test_verify_wrong_password(hasher):
    hashed = hasher.hash("correct-horse-battery-staple")
    assert hasher.verify("wrong-password", hashed) is False


def test_two_hashes_of_same_password_differ(hasher):
    h1 = hasher.hash("same-password")
    h2 = hasher.hash("same-password")
    assert h1 != h2
