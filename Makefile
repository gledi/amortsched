.PHONY: help print-% debug
.PHONY: venv versions lock lock/upgrade lock/up sync/dry sync sync/prod tree list outdated pkg package dev dev/up dev/upgrade

.SILENT: venv versions

.DEFAULT_GOAL := help

SHELL := /bin/bash

PROJECTNAME := $(shell basename $(CURDIR))
PYTHON_VERSION := 3.14
PYENV_PREFIX := $(shell pyenv prefix $(PYTHON_VERSION) 2>/dev/null)
PYTHON_BIN := $(PYENV_PREFIX)/bin/python

VENV_DIR := $(CURDIR)/.venv
VENV_PROMPT := $(PROJECTNAME)-$(PYTHON_VERSION)
PY := $(VENV_DIR)/bin/python

UV := $(shell which uv 2>/dev/null)


define HELP

Manage $(PROJECTNAME).

Usage: make <target>

Where <target> is one of:

  help                   - Show this help message
  print-%                - Print the value of a variable in this Makefile. e.g. make print-PYTHON_BIN
  debug                  - Prints the values of several variables if you need to debug somethng

  venv                   - Create the python virtualenv if it does not exist
  versions               - Show the versions for Python, uv, and this package
  lock                   - Lock dependency versions (updates the uv.lock file or creates it if it doesn't exist)
  lock/up | lock/upgrade - Ensures the depencies in the lock file are upgraded
  sync/dry               - Show what would be installed from the lock file without actually installing anything
  sync                   - Install all dependencies including all extras and dev dependencies from the lock file
  sync/prod              - Install only production dependencies from the lock file
  tree                   - Show the dependency tree
  list                   - List installed packages and their versions using pip style
  outdated               -	List installed packages that have newer versions available using pip style
  pkg | package          - Build the project into a distributable format
  dev                    - Set up a development environment (creates venv, locks and syncs dev dependencies)
  dev/up | dev/upgrade   - Upgrade all dependencies in the lock file and sync the development environment


When no target is specified, the default target is 'help' which shows this message.

endef

export HELP


help:
	@echo "$$HELP"

print-% : ; @echo $* = $($*)

debug: print-PROJECTNAME print-PYTHON_VERSION print-PYENV_PREFIX print-PYTHON_BIN print-VENV_DIR print-VENV_PROMPT print-PY print-UV


venv:
	if ! [[ -d $(VENV_DIR) ]]; then \
		$(UV) venv --no-managed-python --python=$(PY_BIN) --no-project --seed --prompt=$(VENV_PROMPT) --link-mode=copy; \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	fi

versions:
	$(PY) --version
	$(UV) --version
	$(UV) version

lock:
	$(UV) lock --link-mode=copy

lock/up lock/upgrade:
	$(UV) lock --upgrade --refresh --resolution=highest --link-mode=copy

sync/dry:
	$(UV) sync --all-packages --all-extras --all-groups --locked --dry-run

sync:
	$(UV) sync --all-packages --all-extras --all-groups --locked

sync/prod:
	$(UV) sync --all-packages --extra=prod --no-dev --locked

tree:
	$(UV) tree --outdated

list:
	$(UV) pip list

outdated:
	$(UV) pip list --outdated

pkg package:
	$(UV) build --locked

dev: venv lock sync

dev/up dev/upgrade: venv lock/up sync
