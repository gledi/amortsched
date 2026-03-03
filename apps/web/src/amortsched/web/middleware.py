"""Authentication dependencies for FastAPI."""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from amortsched.auth import JoseTokenService
from amortsched.web.deps import get_token_service

_security = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_security),  # noqa: B008
    token_service: JoseTokenService = Depends(get_token_service),  # noqa: B008
) -> uuid.UUID:
    """Extract and validate the user_id from the JWT Bearer token."""
    return token_service.decode_access_token(credentials.credentials)
