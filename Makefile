.DEFAULT_GOAL := help

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
SYSTEM_PYTHON ?= python
SYSTEM_PIP := $(SYSTEM_PYTHON) -m pip
USER_BIN ?= $(HOME)/.local/bin
SYSTEM_BIN ?= /usr/local/bin
SRC_DIRS ?= src tests
TEMPLATE_FILES ?= templates/*.j2

.PHONY: help venv deps dev-deps system-deps pylint flake8 bandit isort mypy pyright ruff j2lint

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

pylint: venv ## Run pylint against source and test code
	$(PYTHON) -m pylint $(SRC_DIRS)

flake8: venv ## Run flake8 against source and test code
	$(PYTHON) -m flake8 $(SRC_DIRS)

bandit: venv ## Run bandit security checks against source code
	$(PYTHON) -m bandit -r src

isort: venv ## Check import ordering without modifying files
	$(PYTHON) -m isort --check-only $(SRC_DIRS)

mypy: venv ## Run mypy static type checks against source code
	$(PYTHON) -m mypy src

pyright: venv ## Run pyright static type checks
	$(VENV)/bin/pyright

ruff: venv ## Run ruff lint checks against source and test code
	$(PYTHON) -m ruff check $(SRC_DIRS)

j2lint: venv ## Run j2lint against Jinja2 templates
	$(VENV)/bin/j2lint $(TEMPLATE_FILES)
