.PHONY: dev sync lock run test lint fmt migrate

dev: sync
	uv run alembic upgrade head

sync:
	uv sync --group dev

lock:
	uv lock

run:
	uv run uvicorn amortsched.api.app:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest -v

lint:
	uv run ruff check src tests

fmt:
	uv run ruff format src tests

migrate:
	uv run alembic revision --autogenerate -m "$(msg)"
