"""FastAPI application."""

from fastapi import FastAPI

from amortsched.core.errors import DomainError
from amortsched.web.errors import domain_error_handler
from amortsched.web.routes.auth import router as auth_router
from amortsched.web.routes.plans import router as plans_router
from amortsched.web.routes.schedules import router as schedules_router
from amortsched.web.routes.users import router as users_router
from amortsched.web.schema import graphql_router

app = FastAPI(title="amortsched")

app.add_exception_handler(DomainError, domain_error_handler)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(plans_router)
app.include_router(schedules_router)
app.include_router(graphql_router, prefix="/graphql")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
