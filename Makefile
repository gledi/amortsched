.DEFAULT_GOAL := help

SHELL := /bin/bash

PROJECTNAME := $(shell basename $(CURDIR))

PY_VERSION := 3.14
UV := $(shell which uv 2>/dev/null)
VENV_DIR := .venv
VENV_PROMPT := $(PROJECTNAME)
PY := $(VENV_DIR)/bin/python

.PHONY: help print-% debug versions
.SILENT: help print-% debug versions

help: ## Show this help
	grep -E '^[a-zA-Z_/%. -]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {target=$$1; gsub(/ +/, " | ", target); printf "\033[36m%-24s\033[0m %s\n", target, $$2}'

print-%: ## Print any variable (e.g. make print-UV)
	echo '$*=$($*)'

print/all: ## Print Makefile variables
	echo "PROJECTNAME  = $(PROJECTNAME)"
	echo "PY_VERSION   = $(PY_VERSION)"
	echo "UV           = $(UV)"
	echo "VENV_DIR     = $(VENV_DIR)"
	echo "VENV_PROMPT  = $(VENV_DIR)"
	echo "PY           = $(PY)"

versions: ## Show Python and uv versions
	echo "uv: $$($(UV) --version 2>/dev/null || echo 'not installed')"
	echo "python: $$($(PY) --version 2>/dev/null || echo 'not found')"


.PHONY: check/uv install/uv venv venv/force
.SILENT: check/uv install/uv venv versions

check/uv: ## Check if uv is installed
	if [ -z "$(UV)" ]; then \
		echo "ERROR: uv is not installed."; \
		echo "  Run: make install/uv"; \
		exit 1; \
	else \
		echo "uv found at $(UV)"; \
	fi

install/uv: ## Install uv via official script
	if [ -z "$(UV)" ]; then \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi

venv: install/uv ## Create virtual environment using uv and pyenv's Python
	if ! [[ -d $(VENV_DIR) ]]; then \
		$(UV) venv --no-project --seed --link-mode=copy --prompt=$(VENV_PROMPT) --python $(PY_VERSION); \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	fi

venv/force: install/uv ## Force-recreate virtual environment
	rm -rf $(VENV_DIR)
	$(UV) venv --no-project --seed --link-mode=copy --prompt=$(VENV_PROMPT) --python $(PY_VERSION)


.PHONY: lock relock sync sync/dry sync/prod outdated tree tree/outdated dev dev/up

lock: ## Lock package versions with upgrades (highest resolution)
	$(UV) lock --refresh --upgrade --resolution=highest

relock: ## Locks uv.lock without upgrading anything
	$(UV) lock

sync/dry: ## Dry-run sync dependencies from all extras and all groups (assumes lock file is up-to-date)
	$(UV) sync --locked --all-extras --dry-run

sync: ## Sync dependencies from all extras and all groups (assumes lock file is up-to-date)
	$(UV) sync --locked --all-extras --link-mode=copy

sync/prod: ## Sync dependencies with only prod extras (assumes lock file is up-to-date)
	$(UV) sync --locked --extra=prod --no-default-groups --link-mode=copy

outdated: ## List outdated packages
	$(UV) pip list --outdated

tree: ## Show dependency tree
	$(UV) tree

tree/outdated: ## Show dependency tree with outdated markers
	$(UV) tree --outdated

dev: venv relock sync ## Quick dev setup (venv + relock + sync), won't upgrade depenencies

dev/up: venv lock sync ## Quick dev setup (venv + lock + sync), NOTE: will upgrade dependencies


.PHONY: test cov test/cov cov/report lint/check lint/fix fmt/check fmt/fix

test: ## Run tests
	uv run --locked pytest --verbose --color=yes --tb=short --maxfail=5

cov test/cov: ## Run tests and gather coverage
	uv run --locked pytest --cov --cov-report= --color=yes --tb=short --maxfail=5

cov/report: ## Show coverage report from last run
	uv run --locked coverage report

lint/check: ## Run ruff linter
	uv run --locked ruff check src/ tests/

lint/fix: ## Auto-fix ruff lint issues
	uv run --locked ruff check --fix src/ tests/

fmt/check: ## Check code formatting
	uv run --locked ruff format --check src/ tests/

fmt/fix: ## Format code with ruff
	uv run --locked ruff format src/ tests/


.PHONY: migrate migrate/new run/api

migrate: ## Apply database migrations
	uv run --locked alembic upgrade head

migrate/new: ## Create new migration (make migrate/new msg="description")
	uv run --locked alembic revision --autogenerate -m "$(msg)"

run/api: ## Start the API server
	uv run --locked uvicorn amortsched.api.app:app --reload --host 0.0.0.0 --port 8000


.PHONY: up up/app up/debug up/app/debug build up/build up/attach down destroy ps top stats start stop restart logs sh

ARGS = $(filter-out $@,$(MAKECMDGOALS))

up: ## Start infra services (db, cache) [service...]
	docker compose up -d --wait $(ARGS)

up/app: ## Start full app stack (app profile) [service...]
	docker compose --profile app up -d --wait $(ARGS)

up/debug up/app/debug: ## Start full app stack with debugpy on :5678 [service...]
	docker compose --profile app -f compose.yml -f compose.debug.yml up -d --wait $(ARGS)

build: ## Build service images [service...]
	docker compose build $(ARGS)

up/build: ## Start services with build [service...]
	docker compose up -d --wait --build $(ARGS)

up/attach: ## Start services in foreground (attached)
	docker compose up

down: ## Stop and remove services
	docker compose down --remove-orphans

destroy: ## Stop, remove services, volumes, and orphans
	docker compose down --volumes --remove-orphans

ps: ## List running services
	docker compose ps

top: ## Show running processes per service
	docker compose top

stats: ## Show live resource usage stats
	docker stats

start: ## Start stopped services [service...]
	docker compose start $(ARGS)

stop: ## Stop services [service...]
	docker compose stop $(ARGS)

restart: ## Restart services [service...]
	docker compose restart $(ARGS)

logs: ## Follow service logs [service]
	docker compose logs -f $(ARGS)

sh: ## Open a shell in a service [service]
	docker compose exec $(ARGS) sh


.PHONY: image/api/dev image/api/prod image/ui/dev image/ui/prod

image/api/dev: ## Build `api` Docker image for development
	docker buildx build --target dev -t $(PROJECTNAME)/api:dev .

image/api/prod: ## Build `api` Docker image for production
	docker buildx build --target prod -t $(PROJECTNAME)/api:prod .

image/ui/dev: ## Build `ui` Docker image for development
	docker buildx build --target dev -t $(PROJECTNAME)/ui:dev ui/

image/ui/prod: ## Build `ui` Docker image for production
	docker buildx build --target prod -t $(PROJECTNAME)/ui:prod ui/


.PHONY: ui/install ui/outdated ui/up ui/build ui/test ui/lint ui/fmt run/ui

ui/install: ## Install UI dependencies
	pnpm --dir ui install

ui/outdated: ## Check for UI outdated dependencies
	pnpm --dir ui outdated

ui/up ui/update: ## Update UI dependencies
	pnpm --dir ui update --save

ui/build: ## Build UI for production
	pnpm --dir ui build

ui/test: ## Run UI tests
	pnpm --dir ui test

ui/lint: ## Lint UI code
	pnpm --dir ui lint

ui/fmt: ## Format UI code
	pnpm --dir ui format

run/ui: ## Start UI dev server
	pnpm --dir ui dev


.PHONY: clean
clean: ## Remove generated files and caches
	rm -rf .pytest_cache/ ui/dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

%:
	@:
