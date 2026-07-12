# Loan Amortization Schedule Generator

A loan amortization schedule generator: a FastAPI backend + React UI that lets users build loan plans and generate detailed amortization schedules.

Schedule engine supports:

- Fixed-rate amortization over a configurable term
- Mid-loan interest rate changes (with configurable proration via `InterestRateApplication`)
- One-time and recurring extra payments
- Early payment fee calculations

Users own **plans** (`draft` → `saved`); each plan generates one or more **schedules** of installments plus totals.

## Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy (async) + psycopg, PostgreSQL, Alembic, Pydantic, structlog
- **Auth**: OAuth2 password flow, JWT access tokens (python-jose), PBKDF2 password hashing, rotating DB-stored refresh tokens
- **Frontend** (`ui/`): React 19, Vite, TanStack Router + Query, Tailwind v4, Base UI, react-hook-form + zod
- **Tooling**: uv, ruff, pytest + anyio + testcontainers, Docker Compose (Traefik, Postgres, Redis)

## Architecture

Ports & adapters (hexagonal) with strict inward-only imports — inner layers never import outer ones. Everything lives in the single `src/amortsched/` package:

```
core      pure domain: entities, amortization engine, value objects,
    ^     errors, repository protocols, specifications  (zero deps)
    |
app       CQRS use cases: commands/ (writes) + queries/ (reads) as
    ^     handler classes; ports.py = Protocol interfaces
    |
adapters  persistence/ (SQLAlchemy async repos, tables, mappers, UoW,
    ^     upsert helpers) + security/ (PBKDF2 hasher, jose JWT)
    |
api       FastAPI: routes/, schemas/; dependencies.py wires handlers
          via Annotated/Depends; session commits on request teardown
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (backend), Docker + Docker Compose
- For local frontend work: Node + pnpm

## Quick start (Docker)

Compose splits infra from app via the `app` profile:

```bash
make up          # infra only: postgres + redis
make up/app      # full stack: traefik + api + ui + postgres + redis
make up/debug    # full stack with debugpy attached on :5678
make migrate     # apply Alembic migrations (needs postgres up)
```

With the app stack running: UI at http://localhost:3000, API under `/api`, Traefik dashboard at http://localhost:8080.

## Local development

```bash
uv sync --all-groups           # install backend deps
make migrate                   # apply migrations (needs a running Postgres)
make run/api                   # uvicorn on :8000, --reload

make ui/install && make run/ui # frontend dev server
```

Config loads from `.env` / environment (pydantic-settings, nested delimiter `__`; see `api/config.py`). Two settings are required — the `app` compose profile sets them for the containerized API; for host-side `make run/api`, put them in a `.env`:

```bash
DATABASE__DSN=postgresql+psycopg://amortsched:amortsched@localhost:5432/amortsched
SECURITY__SECRET_KEY=dev-secret-key-change-in-production
```

## Make targets

```bash
make test                      # pytest (spins up Postgres via testcontainers)
make cov  make cov/report      # run with coverage / show the report
make lint/fix   make fmt/fix   # ruff check --fix / ruff format
make migrate/new msg="..."     # autogenerate a migration
make ui/lint    make ui/build  # frontend lint / production build
```

Run a single test:

```bash
uv run pytest tests/core/test_amortization.py::test_name -v
```

## API endpoints

All under `/api`, JSON, bearer-token auth except register/token.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | Create account |
| POST | `/auth/token` | Log in (OAuth2 password), get access + refresh tokens |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke refresh token |
| GET/PUT | `/users/{id}` · `/users/{id}/profile` | User + profile |
| POST/GET | `/plans` | Create / list plans |
| GET/PATCH/DELETE | `/plans/{id}` | Read / update / delete a plan |
| POST | `/plans/{id}/save` | Promote draft → saved |
| POST | `/plans/{id}/extra-payments` · `/recurring-extra-payments` · `/interest-rate-changes` | Add plan adjustments |
| POST/GET | `/plans/{id}/schedules` | Generate / list schedules |
| GET/DELETE | `/plans/{id}/schedules/{sid}` | Read / delete a schedule |
| POST | `/plans/{id}/schedules/{sid}/save` | Persist a generated schedule |

Interactive docs at `/docs` when the API is running.
