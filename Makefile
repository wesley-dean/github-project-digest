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
APP_NAME ?= github-project-digest

.PHONY: help venv deps dev-deps system-deps pylint flake8 bandit isort mypy pyright ruff j2lint format check test all install system-install

help: ## Show available Make targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

venv: ## Create the local virtual environment when it does not already exist
	@test -x $(PYTHON) || $(SYSTEM_PYTHON) -m venv $(VENV)

deps: venv ## Install runtime dependencies locally
	$(PIP) install -e .

dev-deps: venv ## Install development dependencies locally
	$(PIP) install -e '.[dev]'

system-deps: ## Install development dependencies globally
	$(SYSTEM_PIP) install -e '.[dev]'

pylint: venv ## Run pylint
	$(PYTHON) -m pylint $(SRC_DIRS)

flake8: venv ## Run flake8
	$(PYTHON) -m flake8 $(SRC_DIRS)

bandit: venv ## Run bandit
	$(PYTHON) -m bandit -r src

isort: venv ## Check import ordering
	$(PYTHON) -m isort --check-only $(SRC_DIRS)

mypy: venv ## Run mypy
	$(PYTHON) -m mypy src

pyright: venv ## Run pyright
	$(VENV)/bin/pyright

ruff: venv ## Run ruff checks
	$(PYTHON) -m ruff check $(SRC_DIRS)

j2lint: venv ## Run j2lint
	$(VENV)/bin/j2lint $(TEMPLATE_FILES)

format: venv ## Format code
	$(PYTHON) -m ruff format $(SRC_DIRS)

check: pylint flake8 bandit isort mypy pyright ruff j2lint ## Run all checks

test: venv ## Run tests
	PYTHONPATH=src $(PYTHON) -m pytest -q

all: deps dev-deps format check test ## Run the full local quality workflow

install: deps ## Copy the console script into the user-local bin directory
	mkdir -p $(USER_BIN)
	cp $(VENV)/bin/$(APP_NAME) $(USER_BIN)/$(APP_NAME)
	chmod 755 $(USER_BIN)/$(APP_NAME)

system-install: deps ## Copy the console script into the system bin directory
	mkdir -p $(SYSTEM_BIN)
	cp $(VENV)/bin/$(APP_NAME) $(SYSTEM_BIN)/$(APP_NAME)
	chmod 755 $(SYSTEM_BIN)/$(APP_NAME)
