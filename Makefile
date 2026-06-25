.DEFAULT_GOAL := help

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
SYSTEM_PYTHON ?= python
SYSTEM_PIP := $(SYSTEM_PYTHON) -m pip
USER_BIN ?= $(HOME)/.local/bin
SYSTEM_BIN ?= /usr/local/bin

.PHONY: help venv deps dev-deps system-deps

help: ## Show available Make targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

venv: ## Create the local virtual environment when it does not already exist
	@test -x $(PYTHON) || $(SYSTEM_PYTHON) -m venv $(VENV)

deps: venv ## Install the project and runtime dependencies into the local virtual environment
	$(PIP) install -e .

dev-deps: venv ## Install the project, runtime dependencies, and developer checker dependencies into the local virtual environment
	$(PIP) install -e '.[dev]'

system-deps: ## Install the project, runtime dependencies, and developer checker dependencies with the system Python
	$(SYSTEM_PIP) install -e '.[dev]'
