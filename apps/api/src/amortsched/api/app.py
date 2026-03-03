"""Starlette ASGI application."""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from amortsched.api.deps import build_container
from amortsched.api.errors import domain_error_handler
from amortsched.api.routes.auth import routes as auth_routes
from amortsched.api.routes.plans import routes as plan_routes
from amortsched.api.routes.schedules import routes as schedule_routes
from amortsched.api.routes.users import routes as user_routes
from amortsched.core.errors import DomainError


async def health(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


routes = [
    Route("/health", health, methods=["GET"]),
    *auth_routes,
    *user_routes,
    *plan_routes,
    *schedule_routes,
]

app = Starlette(debug=False, routes=routes)
app.state.container = build_container()
app.add_exception_handler(DomainError, domain_error_handler)
