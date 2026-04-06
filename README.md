# Loan Amortization Schedule Generator

A loan amortization schedule generator built as a Python uv workspace following ports & adapters (hexagonal) architecture and clean architecture principles.

Generates detailed amortization schedules with support for:

- Variable interest rates (with configurable proration strategies)
- One-time and recurring extra payments
- Early payment fee calculations

## Architecture

The codebase follows a strict layering model where inner layers never import from outer layers:

```
   core   (pure logic, zero dependencies)
    ^
    |
   app    (use cases + ports, depends only on core)
    ^
    |
 adapters (data-inmemory, data-sqlalchemy, data-mongo)
    ^
    |
   apps   (cli, api-starlette, api-fastapi)
```

All packages live under the `amortsched` namespace:

| Package | Import path | Description |
|---------|-------------|-------------|
| `amortsched-core` | `amortsched.core` | Entities, amortization logic, value objects, errors |
| `amortsched-app` | `amortsched.app` | Use cases (services) and ports (repository protocols) |
| `amortsched-data-inmemory` | `amortsched.data.inmemory` | In-memory repository implementations |
| `amortsched-data-sqlalchemy` | `amortsched.data.sqlalchemy` | SQLAlchemy repositories (stub) |
| `amortsched-data-mongo` | `amortsched.data.mongo` | MongoDB repositories (stub) |
| `amortsched-cli` | `amortsched.cli` | Click-based CLI application |
| `amortsched-api-starlette` | `amortsched.api.starlette` | Starlette REST API |
| `amortsched-api-fastapi` | `amortsched.api.fastapi` | FastAPI REST + Strawberry GraphQL API |

## Workspace Structure

```
amortsched/
├── pyproject.toml                           # workspace root
├── apps/
│   ├── cli/                                 # amortsched.cli
│   ├── api-starlette/                       # amortsched.api.starlette
│   └── api-fastapi/                         # amortsched.api.fastapi
└── libs/
    ├── core/                               # amortsched.core
    ├── app/                                 # amortsched.app
    ├── data-inmemory/                       # amortsched.data.inmemory
    ├── data-sqlalchemy/                     # amortsched.data.sqlalchemy
    └── data-mongo/                          # amortsched.data.mongo
```

Each member uses `src/amortsched/<subpackage>/` layout with hatchling as the build backend.

## Package Dependency Graph

```
amortsched-cli ──────────────┐
amortsched-api-starlette ────┤
amortsched-api-fastapi ──────┤
                             ├──> amortsched-data-inmemory ──> amortsched-app ──> amortsched-core
amortsched-data-sqlalchemy ──┘                                      ^
amortsched-data-mongo ──────────────────────────────────────────────┘
```

## Prerequisites

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/)

## Development Setup

```bash
# Install all dependencies (dev + test + all workspace members)
uv sync --all-extras --all-groups

# Activate the virtual environment (or use `uv run` prefix)
source .venv/bin/activate
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific package
uv run pytest libs/core/tests/ -v

# Run a specific test
uv run pytest libs/core/tests/test_amortization.py::test_amortization_schedule_without_extra_payments -v
```

## Linting

```bash
# Check for lint errors
uv run ruff check

# Auto-fix lint errors
uv run ruff check --fix

# Format code
uv run ruff format
```

## Running Applications

```bash
# CLI - generate an amortization schedule
uv run amortsched schedule --rate 5.5 --years 30 100000

# CLI - with extra payments
uv run amortsched schedule --rate 5.5 --years 30 --extra 2025-06-15:10000 100000
```
