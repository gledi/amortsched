.DEFAULT_GOAL := help

SHELL := /bin/bash

PROJECTNAME := $(shell basename $(CURDIR))

PY_VERSION := 3.14
UV := $(shell which uv 2>/dev/null)
PYENV_PREFIX := $(shell pyenv prefix $(PY_VERSION) 2>/dev/null)
PYENV_PYTHON_BIN := $(if $(PYENV_PREFIX),$(PYENV_PREFIX)/bin/python,)
VENV_DIR := $(CURDIR)/.venv
VENV_PROMPT := $(PROJECTNAME)
PY := $(VENV_DIR)/bin/python


.PHONY: help print-% debug versions
.SILENT: help print-% debug versions

help: ## Show this help
	grep -E '^[a-zA-Z_/%. -]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {target=$$1; gsub(/ +/, " | ", target); printf "\033[36m%-24s\033[0m %s\n", target, $$2}'

print-%: ## Print any variable (e.g. make print-UV)
	echo '$*=$($*)'

debug: ## Print key Makefile variables
	echo "PROJECTNAME      = $(PROJECTNAME)"
	echo "PY_VERSION       = $(PY_VERSION)"
	echo "UV               = $(UV)"
	echo "PYENV_PREFIX     = $(PYENV_PREFIX)"
	echo "PYENV_PYTHON_BIN = $(PYENV_PYTHON_BIN)"
	echo "VENV_DIR         = $(VENV_DIR)"
	echo "PY               = $(PY)"

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
		$(UV) venv --no-project --seed --prompt=$(VENV_PROMPT) --link-mode=copy --no-managed-python --python=$(PYENV_PYTHON_BIN); \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	fi

venv/force: install/uv ## Force-recreate virtual environment
	rm -rf $(VENV_DIR)
	$(UV) venv --no-project --seed --prompt=$(VENV_PROMPT) --link-mode=copy --no-managed-python --python=$(PYENV_PYTHON_BIN)


.PHONY: lock lock/up sync sync/dev outdated tree dev

lock: ## Lock dependencies
	$(UV) lock --link-mode=copy

lock/up: ## Lock with upgrades (highest resolution)
	$(UV) lock --refresh --upgrade --resolution=highest --link-mode=copy

sync sync/dev: ## Sync dev dependencies (frozen)
	$(UV) sync --locked --all-groups --no-install-project --link-mode=copy

outdated: ## List outdated packages
	$(UV) pip list --outdated

tree: ## Show dependency tree with outdated markers
	$(UV) tree --outdated

dev: venv lock/up sync/dev ## Quick dev setup (venv + lock/up + sync/dev)


.PHONY: test lint/check lint/fix fmt/check fmt/fix

test: ## Run tests
	uv run pytest -v

lint/check: ## Run ruff linter
	uv run ruff check src/ tests/

lint/fix: ## Auto-fix ruff lint issues
	uv run ruff check --fix src/ tests/

fmt/check: ## Check code formatting
	uv run ruff format --check src/ tests/

fmt/fix: ## Format code with ruff
	uv run ruff format src/ tests/


.PHONY: migrate migrate/new run/api

migrate: ## Apply database migrations
	uv run alembic upgrade head

migrate/new: ## Create new migration (make migrate/new msg="description")
	uv run alembic revision --autogenerate -m "$(msg)"

run/api: ## Start the API server
	uv run uvicorn amortsched.api.app:app --reload --host 0.0.0.0 --port 8000


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
