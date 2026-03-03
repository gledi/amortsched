"""Application-layer port protocols."""

import uuid
from typing import Protocol


class TokenService(Protocol):
    """Port for creating and decoding access tokens."""

    def create_access_token(self, user_id: uuid.UUID) -> str: ...

    def decode_access_token(self, token: str) -> uuid.UUID: ...
