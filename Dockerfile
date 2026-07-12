# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14
ARG UV_VERSION=0.11.31

FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python${PYTHON_VERSION}-trixie-slim AS deps

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --no-install-project --no-editable


FROM deps AS builder

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --no-editable


FROM deps AS dev-builder

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups --no-install-project

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups


FROM python:${PYTHON_VERSION}-slim-trixie AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"

RUN useradd --system --user-group --no-create-home --shell /sbin/nologin appuser

USER appuser

WORKDIR /app


FROM base AS dev

COPY --from=dev-builder /app/.venv/ /app/.venv/
COPY --from=dev-builder /app/src/ /app/src/


FROM base AS prod

EXPOSE 8000

COPY --from=builder /app/.venv/ /app/.venv/
COPY alembic.ini ./

CMD ["uvicorn", "amortsched.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
