# Loan Amortization Schedule Generator

Plan mortgages and loans, compare offers, and decide with numbers: a FastAPI backend + React UI.

- **Plans**: mortgages, auto, personal, and student loans in any currency, with lender, upfront fees, prepayment penalties, and (for mortgages) home price, down payment, property tax, insurance, HOA, and PMI that cancels at a configurable LTV.
- **Schedules**: fixed or adjustable rates (dated rate changes with configurable proration), one-time and recurring extra payments, full monthly payment including ownership costs, CSV export, printable view.
- **Comparison**: two to four offers side by side; total cost (payments + upfront fees + PMI), cost if you sell or refinance after N years (including payoff penalty), and a cost-over-time chart showing where offers cross.
- **Decision tools**: home affordability (28/36 debt-to-income), refinance break-even, prepay vs. invest.
- **Accounts**: email verification, password reset, change password, sign out other devices, data export, account deletion.

Domain vocabulary lives in `CONTEXT.md`.

## Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy (async) + psycopg, PostgreSQL, Alembic, Pydantic, structlog
- **Auth**: OAuth2 password flow, short-lived PyJWT access tokens, rotating DB-stored refresh tokens in an httpOnly `SameSite=Strict` cookie, PBKDF2 hashing, fixed-window rate limiting (in-memory or Redis)
- **Frontend** (`ui/`): React 19, Vite, TanStack Router + Query, Tailwind v4, Base UI, react-hook-form + zod
- **Tooling**: uv, ruff, pytest + anyio + testcontainers, Docker Compose (Traefik, Postgres, Redis, Mailpit)

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
    ^     upsert helpers) + security/ (PBKDF2 hasher, PyJWT)
    |
api       FastAPI: routes/, schemas/; dependencies.py wires handlers
          via Annotated/Depends; session commits before the response
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (backend), Docker + Docker Compose
- For local frontend work: Node + pnpm

## Quick start (Docker)

Compose splits infra from app via the `app` profile:

```bash
make up          # infra only: postgres + redis + mailpit
make up/app      # full stack: traefik + api + ui + postgres + redis + mailpit
make up/debug    # full stack with debugpy attached on :5678
make migrate     # apply Alembic migrations (needs postgres up)
```

With the app stack running: UI at http://localhost:3000, API under `/api`, Traefik dashboard at http://localhost:8080, and every email the app sends at http://localhost:8025 (Mailpit).

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

Optional settings (defaults shown in parentheses):

| Variable | Purpose |
|----------|---------|
| `PUBLIC_URL` (`http://localhost:3000`) | Base URL for links in emails |
| `EMAIL__BACKEND` (`console`) | `console` logs emails; `smtp` sends them |
| `EMAIL__HOST` / `EMAIL__PORT` / `EMAIL__USERNAME` / `EMAIL__PASSWORD` / `EMAIL__STARTTLS` / `EMAIL__USE_SSL` / `EMAIL__SENDER` | SMTP delivery; any provider with SMTP works (Mailpit in dev) |
| `RATE_LIMIT__BACKEND` (`memory`) | `redis` to share limits across processes, with `RATE_LIMIT__REDIS_URL` |
| `RATE_LIMIT__ENABLED` (`true`) | Turn rate limiting off |
| `SECURITY__COOKIE_SECURE` (`true`) | Set `false` only when serving over plain HTTP on a non-localhost host |

Behind a proxy, run uvicorn with `--proxy-headers` so rate limits see client IPs. The UI dev server proxies `/api` to `API_PROXY_TARGET` (default `http://localhost:8000`).

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

All under `/api`, JSON. Everything except the `/auth` routes needs a bearer access token. The refresh token travels only in the httpOnly cookie.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | Create account, send verification email, start a session |
| POST | `/auth/token` | Log in (OAuth2 password form) |
| POST | `/auth/refresh` · `/auth/logout` | Rotate / revoke the session cookie |
| POST | `/auth/verify-email` | Confirm an email with the emailed token |
| POST | `/auth/password-reset/request` · `/confirm` | Email a reset link / set a new password |
| GET/PATCH/DELETE | `/users/me` | Read / rename / delete (password required) the account |
| GET/PUT | `/users/me/profile` | Display preferences, default currency, locale |
| POST | `/users/me/password` · `/users/me/sessions/revoke` · `/users/me/verification-email` | Change password / sign out other devices / resend verification |
| GET | `/users/me/export` | Download all account data as JSON |
| POST/GET | `/plans` | Create (optionally with adjustments) / list plans |
| GET/PATCH/DELETE | `/plans/{id}` | Read / update / delete a plan |
| PUT | `/plans/{id}/adjustments` | Replace extra payments and rate changes |
| POST | `/plans/{id}/extra-payments` · `/recurring-extra-payments` · `/interest-rate-changes` | Append one adjustment |
| POST | `/plans/{id}/duplicate` · `/plans/{id}/save` | Copy a plan / promote draft → saved |
| GET | `/plans/{id}/schedule.csv` | Export a freshly generated schedule |
| POST/GET | `/plans/{id}/schedules` | Generate and persist / list schedules |
| GET/DELETE | `/plans/{id}/schedules/{sid}` | Read / delete a schedule |
| POST | `/plan-comparisons/preview` | Compare 2–4 plans, optionally at a `horizon_months` |
| POST | `/tools/affordability` · `/tools/refinance` · `/tools/prepay-vs-invest` | Decision calculators |

Interactive docs at `/docs` when the API is running.
