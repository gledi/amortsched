import hashlib
import secrets


class PBKDF2PasswordHasher:
    _DEFAULT_ITERATIONS: int = 600_000

    def __init__(self, iterations: int | None = None) -> None:
        self._iterations: int = iterations if iterations is not None else self._DEFAULT_ITERATIONS

    def hash(self, password: str) -> str:
        salt = secrets.token_hex(16)
        hash_hex = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), self._iterations).hex()
        return f"pbkdf2${salt}${hash_hex}"

    def verify(self, password: str, password_hash: str) -> bool:
        _, salt, stored_hash = password_hash.split("$", 2)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), self._iterations).hex()
        return secrets.compare_digest(stored_hash, candidate)


class ScryptPasswordHasher:
    _cost_factor: int = 2**14
    _block_size: int = 8
    _parallelization_factor: int = 1

    def __init__(self, n: int | None = None, r: int | None = None, p: int | None = None) -> None:
        self._n: int = n if n is not None else self._cost_factor
        self._r: int = r if r is not None else self._block_size
        self._p: int = p if p is not None else self._parallelization_factor

    def hash(self, password: str) -> str:
        salt = secrets.token_hex(16)
        hash_hex = hashlib.scrypt(password.encode(), salt=salt.encode(), n=self._n, r=self._r, p=self._p).hex()
        return f"scrypt${salt}${hash_hex}"

    def verify(self, password: str, password_hash: str) -> bool:
        _, salt, stored_hash = password_hash.split("$", 2)
        candidate = hashlib.scrypt(password.encode(), salt=salt.encode(), n=self._n, r=self._r, p=self._p).hex()
        return secrets.compare_digest(stored_hash, candidate)
