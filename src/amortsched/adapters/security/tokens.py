"""JWT access-token service."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from amortsched.core.errors import ExpiredTokenError, InvalidTokenError


class JwtTokenService:
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 30) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def create_access_token(self, user_id: uuid.UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> uuid.UUID:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError() from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        sub = payload.get("sub")
        if sub is None:
            raise InvalidTokenError("Token missing subject claim")

        try:
            return uuid.UUID(str(sub))
        except ValueError as exc:
            raise InvalidTokenError("Invalid subject in token") from exc

    def create_refresh_token(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
