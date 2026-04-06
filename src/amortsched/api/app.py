from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from amortsched.api.config import get_settings
from amortsched.api.errors import domain_error_handler
from amortsched.api.middleware import RequestLoggingMiddleware
from amortsched.api.routes.auth import router as auth_router
from amortsched.api.routes.plans import router as plans_router
from amortsched.api.routes.schedules import router as schedules_router
from amortsched.api.routes.users import router as users_router
from amortsched.core.errors import DomainError


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    app.state.async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    configure_structlog()
    app = FastAPI(title="Amortization Schedule API", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(plans_router)
    app.include_router(schedules_router)
    return app


app = create_app()
