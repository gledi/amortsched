"""RFC 9457 Problem Details error handling for FastAPI."""

from fastapi import Request
from fastapi.responses import JSONResponse

from amortsched.core.errors import (
    AmortizationError,
    AuthenticationError,
    DomainError,
    DuplicateEmailError,
    ExpiredTokenError,
    InvalidTokenError,
    NotFoundError,
    PlanOwnershipError,
)

_URN_PREFIX = "urn:amortsched"

_ERROR_MAP: list[tuple[type[DomainError], int, str, str]] = [
    (ExpiredTokenError, 401, "/errors/token-expired", "Token Expired"),
    (InvalidTokenError, 401, "/errors/invalid-token", "Invalid Token"),
    (AuthenticationError, 401, "/errors/authentication-failed", "Authentication Failed"),
    (PlanOwnershipError, 403, "/errors/forbidden", "Forbidden"),
    (NotFoundError, 404, "/errors/not-found", "Not Found"),
    (DuplicateEmailError, 409, "/errors/duplicate-email", "Duplicate Email"),
    (AmortizationError, 422, "/errors/validation", "Validation Error"),
]


def domain_error_to_problem(exc: DomainError) -> tuple[int, dict]:
    """Convert a domain error to (status_code, RFC 9457 body dict)."""
    for error_type, status, type_suffix, title in _ERROR_MAP:
        if isinstance(exc, error_type):
            return status, {
                "type": f"{_URN_PREFIX}{type_suffix}",
                "title": title,
                "status": status,
                "detail": str(exc),
            }
    return 400, {
        "type": f"{_URN_PREFIX}/errors/domain-error",
        "title": "Domain Error",
        "status": 400,
        "detail": str(exc),
    }


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """FastAPI exception handler for DomainError."""
    assert isinstance(exc, DomainError)
    status, body = domain_error_to_problem(exc)
    return JSONResponse(body, status_code=status, media_type="application/problem+json")
