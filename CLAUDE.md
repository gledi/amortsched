FastAPI amortization-schedule API (Python 3.14, uv, PostgreSQL) + React 19 UI, hexagonal architecture.

**Ignore README.md's architecture section** — it describes an outdated multi-package workspace. Real code is a single `src/amortsched/` package.

## Commands (Makefile is canonical)

- `make test` — pytest. Single test: `uv run pytest tests/core/test_amortization.py::test_name`
- `make lint/fix` / `make fmt/fix` — ruff check/format (line length 120)
- `make run/api` — uvicorn dev server (:8000)
- `make migrate` — alembic upgrade head; `make migrate/new msg="..."` — autogenerate migration
- `make up` — docker compose (traefik :3000 → api, ui, postgres, redis)
- UI (`ui/`, pnpm): `make run/ui`, `make ui/build`, `make ui/lint`, `make ui/fmt`

Tests spin up a real Postgres via testcontainers (session-scoped fixture in `tests/conftest.py`).

## Architecture — strict inward-only layering, `src/amortsched/`

- `core/` — pure domain, zero deps: entities, `amortization.py`, values, errors, repository *protocols*, specifications
- `app/` — CQRS use cases: `commands/` (writes) + `queries/` (reads) as handler classes; `ports.py` = Protocol interfaces (Settings, TokenService, UnitOfWork)
- `adapters/` — `persistence/` (SQLAlchemy async repos, tables, mappers, uow, upsert helpers) + `security/` (PBKDF2 hasher, jose JWT)
- `api/` — FastAPI: `routes/`, `schemas/`; `dependencies.py` wires every handler via `Annotated`/`Depends`; `get_session` commits on request teardown

Inner layers never import outer. Auth = OAuth2 bearer, JWT access tokens + DB-stored refresh tokens.

## Superpowers artifacts

Keep under `.superpowers/` (specs → `.superpowers/specs`, plans → `.superpowers/plans`, etc.), not `docs/`. Already git-ignored — don't track.
