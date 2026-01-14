import pytest

from amortsched.security import Argon2PasswordHasher, BcryptPasswordHasher, PBKDF2PasswordHasher, ScryptPasswordHasher


@pytest.fixture(
    params=[PBKDF2PasswordHasher, BcryptPasswordHasher, ScryptPasswordHasher, Argon2PasswordHasher],
    ids=["pbkdf2", "bcrypt", "scrypt", "argon2"],
)
def hasher(request):
    return request.param()


class TestPasswordHasher:
    def test_hash_returns_non_empty_string(self, hasher):
        result = hasher.hash("password123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_verify_correct_password(self, hasher):
        hashed = hasher.hash("correct-horse-battery-staple")
        assert hasher.verify("correct-horse-battery-staple", hashed) is True

    def test_verify_wrong_password(self, hasher):
        hashed = hasher.hash("correct-horse-battery-staple")
        assert hasher.verify("wrong-password", hashed) is False

    def test_two_hashes_of_same_password_differ(self, hasher):
        h1 = hasher.hash("same-password")
        h2 = hasher.hash("same-password")
        assert h1 != h2
