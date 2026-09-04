.DEFAULT_GOAL := help

SHELL := /bin/bash

PROJECTNAME := $(shell basename $(CURDIR))

PY_VERSION := 3.14
UV := $(shell which uv 2>/dev/null)
VENV_DIR := .venv
VENV_PROMPT := $(PROJECTNAME)
PY := $(VENV_DIR)/bin/python

ARGS = $(filter-out $@,$(MAKECMDGOALS))


.PHONY: help print-% print/all versions
.SILENT: help print-% print/all versions

##@ Meta
help: ## Show this help
	@echo ""
	@echo "Manage $(PROJECTNAME). Usage:"
	@awk 'BEGIN{FS=":.*##"} \
	     /^##@/{printf "\n\033[1m%s\033[0m\n",substr($$0,5);next} \
	     /^[a-zA-Z0-9_%\/. -]+:.*##/{n=$$1; gsub(/ +/," | ",n); printf "  \033[36m%-24s\033[0m %s\n",n,$$2}' $(MAKEFILE_LIST)
	@echo ""

print-%: ## Print a variable (e.g. make print-UV)
	@echo '$*=$($*)'

print/all: ## Print key Makefile variables
	@echo "PROJECTNAME  = $(PROJECTNAME)"
	@echo "PY_VERSION   = $(PY_VERSION)"
	@echo "UV           = $(UV)"
	@echo "VENV_DIR     = $(VENV_DIR)"
	@echo "VENV_PROMPT  = $(VENV_PROMPT)"
	@echo "PY           = $(PY)"

versions: ## Show uv, Python and project versions
	@echo "uv: $$($(UV) --version 2>/dev/null || echo 'not installed')"
	@echo "python: $$($(PY) --version 2>/dev/null || echo 'not found')"


.PHONY: check/uv install/uv venv venv/force
.SILENT: check/uv install/uv venv

##@ Environment
check/uv: ## Check that uv is installed
	@if [ -z "$(UV)" ]; then \
		echo "ERROR: uv is not installed."; \
		echo "  Run: make install/uv"; \
		exit 1; \
	else \
		echo "uv found at $(UV)"; \
	fi

install/uv: ## Install uv via official script
	@if [ -z "$(UV)" ]; then \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi

venv: install/uv ## Create virtual environment (skips if exists)
	@if ! [[ -d $(VENV_DIR) ]]; then \
		$(UV) venv --no-project --seed --link-mode=copy --prompt=$(VENV_PROMPT) --python $(PY_VERSION); \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	fi

venv/force: install/uv ## Force-recreate virtual environment
	rm -rf $(VENV_DIR)
	$(UV) venv --no-project --seed --link-mode=copy --prompt=$(VENV_PROMPT) --python $(PY_VERSION)


.PHONY: lock relock sync sync/prod sync/dry outdated tree tree/outdated dev dev/up

##@ Dependencies
lock: ## Lock dependencies with upgrades (highest resolution)
	$(UV) lock --refresh --upgrade --resolution=highest

relock: ## Re-lock without upgrading anything
	$(UV) lock

sync: ## Sync all dependencies from lockfile
	$(UV) sync --locked --all-extras --link-mode=copy

sync/prod: ## Sync runtime + prod deps only (no dev groups)
	$(UV) sync --locked --extra=prod --no-default-groups --link-mode=copy

sync/dry: ## Dry-run sync from lockfile
	$(UV) sync --locked --all-extras --dry-run

outdated: ## List outdated packages
	$(UV) pip list --outdated

tree: ## Show dependency tree
	$(UV) tree

tree/outdated: ## Show dependency tree with outdated markers
	$(UV) tree --outdated

dev: venv relock sync ## Full dev setup: venv + re-lock + sync (no upgrade)

dev/up: venv lock sync ## Full dev setup: venv + lock + sync (upgrades deps)


.PHONY: test cov test/cov cov/report lint/check lint lint/fix fmt/check fmt fmt/fix typecheck

##@ Lint & format
lint/check lint: ## Check for linting issues with ruff
	uv run --locked ruff check src/ tests/

lint/fix: ## Auto-fix ruff lint issues (WARNING: modifies files!)
	uv run --locked ruff check --fix src/ tests/

fmt/check fmt: ## Check code formatting with ruff
	uv run --locked ruff format --check src/ tests/

fmt/fix: ## Format code with ruff (WARNING: modifies files!)
	uv run --locked ruff format src/ tests/

typecheck: ## Run basedpyright type checker
	uv run --locked basedpyright


##@ Test
test: ## Run tests
	uv run --locked pytest

cov test/cov: ## Run tests with coverage
	uv run --locked pytest --cov --cov-report=

cov/report: ## Show coverage report from last run
	uv run --locked coverage report


.PHONY: migrate migrate/new migrate/status migrate/history run/api

##@ Database & migrations
migrate: ## Apply all pending database migrations
	uv run --locked alembic upgrade head

migrate/new: ## Create new migration (make migrate/new msg="description")
	uv run --locked alembic revision --autogenerate -m "$(msg)"

migrate/status: ## Show current DB revision and latest head(s)
	uv run --locked alembic current
	uv run --locked alembic heads

migrate/history: ## Show full migration history
	uv run --locked alembic history --verbose


##@ Run
run/api: ## Start the API dev server (uvicorn, autoreload)
	uv run --locked uvicorn amortsched.api.app:app --reload --host 0.0.0.0 --port 8000


.PHONY: up up/app up/debug build up/build up/attach down destroy ps top stats start stop restart logs sh

##@ Compose
up: ## Start infra services (db, cache) [service...]
	docker compose up -d --wait $(ARGS)

up/app: ## Start full app stack (app profile) [service...]
	docker compose --profile app up -d --wait $(ARGS)

up/debug up/app/debug: ## Start app stack with debugpy on :5678 [service...]
	docker compose --profile app -f compose.yml -f compose.debug.yml up -d --wait $(ARGS)

build: ## Build service images [service...]
	docker compose build $(ARGS)

up/build: ## Start services with build [service...]
	docker compose up -d --wait --build $(ARGS)

up/attach: ## Start services in foreground (attached)
	docker compose up

down: ## Stop and remove services
	docker compose down --remove-orphans

destroy: ## Stop, remove services AND volumes
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

##@ Images
image/api/dev: ## Build api Docker image (dev)
	docker buildx build --target dev -t $(PROJECTNAME)/api:dev .

image/api/prod: ## Build api Docker image (prod)
	docker buildx build --target prod -t $(PROJECTNAME)/api:prod .

image/ui/dev: ## Build ui Docker image (dev)
	docker buildx build --target dev -t $(PROJECTNAME)/ui:dev ui/

image/ui/prod: ## Build ui Docker image (prod)
	docker buildx build --target prod -t $(PROJECTNAME)/ui:prod ui/


.PHONY: ui/install ui/outdated ui/up ui/update ui/build ui/test ui/lint ui/fmt run/ui

##@ UI (pnpm)
ui/install: ## Install UI dependencies
	pnpm --dir ui install

ui/outdated: ## Check for outdated UI dependencies
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

##@ Build & clean
clean: ## Remove generated files and caches
	rm -rf .pytest_cache/ ui/dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

%:
	@:
