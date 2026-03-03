"""Application-layer port protocols."""

import uuid
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class TokenService(Protocol):
    """Port for creating and decoding access tokens."""

    def create_access_token(self, user_id: uuid.UUID) -> str: ...

    def decode_access_token(self, token: str) -> uuid.UUID: ...


class Validator(Protocol[T]):
    """Port for validating and serializing API schema types."""

    def validate(self, data: dict[str, Any]) -> T:
        """Parse and validate a dict into a schema instance.

        Raises ValidationError (from core) on invalid data.
        """
        ...

    def serialize(self, obj: T) -> dict[str, Any]:
        """Serialize a schema instance to a plain dict.

        The returned dict uses camelCase keys suitable for JSON responses.
        """
        ...
