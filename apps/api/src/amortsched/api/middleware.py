"""Authentication middleware for Starlette."""

import uuid

from starlette.exceptions import HTTPException
from starlette.requests import Request

from amortsched.auth import JoseTokenService


def get_current_user_id(request: Request) -> uuid.UUID:
    """Extract and validate the JWT from the Authorization header.

    Returns the user_id from the token. Raises domain errors
    (InvalidTokenError, ExpiredTokenError) on failure — these are
    caught by the domain error handler and converted to RFC 9457 responses.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = auth_header.removeprefix("Bearer ")
    token_service: JoseTokenService = request.app.state.container.resolve(JoseTokenService)
    return token_service.decode_access_token(token)
