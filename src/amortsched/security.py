import hashlib
import secrets
from typing import Protocol

import argon2
import bcrypt


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, password_hash: str) -> bool: ...


class PBKDF2PasswordHasher:
    _DEFAULT_ITERATIONS = 600_000

    def __init__(self, iterations: int | None = None) -> None:
        self._iterations = iterations if iterations is not None else self._DEFAULT_ITERATIONS

    def hash(self, password: str) -> str:
        salt = secrets.token_hex(16)
        hash_hex = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), self._iterations).hex()
        return f"pbkdf2${salt}${hash_hex}"

    def verify(self, password: str, password_hash: str) -> bool:
        _, salt, stored_hash = password_hash.split("$", 2)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), self._iterations).hex()
        return secrets.compare_digest(stored_hash, candidate)


class BcryptPasswordHasher:
    _DEFAULT_ROUNDS = 12

    def __init__(self, rounds: int | None = None) -> None:
        self._DEFAULT_ROUNDS = rounds if rounds is not None else self._DEFAULT_ROUNDS

    def hash(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=self._DEFAULT_ROUNDS)
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())


class ScryptPasswordHasher:
    _n = _cost_factor = 2**14
    _r = _block_size = 8
    _p = _parallelization_factor = 1

    def __init__(self, n: int | None = None, r: int | None = None, p: int | None = None) -> None:
        self._n = n if n is not None else self._n
        self._r = r if r is not None else self._r
        self._p = p if p is not None else self._p

    def hash(self, password: str) -> str:
        salt = secrets.token_hex(16)
        hash_hex = hashlib.scrypt(password.encode(), salt=salt.encode(), n=self._n, r=self._r, p=self._p).hex()
        return f"scrypt${salt}${hash_hex}"

    def verify(self, password: str, password_hash: str) -> bool:
        _, salt, stored_hash = password_hash.split("$", 2)
        candidate = hashlib.scrypt(password.encode(), salt=salt.encode(), n=self._n, r=self._r, p=self._p).hex()
        return secrets.compare_digest(stored_hash, candidate)


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = argon2.PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except argon2.exceptions.VerifyMismatchError:
            return False
