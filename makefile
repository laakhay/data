SHELL := /bin/sh

# Require uv - fail if not available
UV := $(shell command -v uv 2>/dev/null)
ifeq ($(UV),)
  $(error uv is required but not found. Install it from https://github.com/astral-sh/uv)
endif

# Python version from pyproject.toml (requires-python = ">=3.12")
PYTHON_VERSION ?= 3.12
PY := $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: help install test unit-test integration-test lint format format-check type-check fix coverage clean build publish

help:
	@echo "Make targets:"
	@echo "  install         Install project and dev dependencies from pyproject.toml."
	@echo "  test            Run all tests (unit + integration)."
	@echo "  unit-test       Run unit test suite (tests/unit)."
	@echo "  integration-test Run integration tests (tests/integration)."
	@echo "  lint            Run ruff lint if available."
	@echo "  format          Run ruff format if available."
	@echo "  format-check    Check if code formatting is correct."
	@echo "  type-check      Run mypy type checker."
	@echo "  fix             Auto-fix linting issues and format code."
	@echo "  coverage        Run tests with coverage report."
	@echo "  clean           Remove caches and compiled artifacts."
	@echo "  build           Build distribution packages."
	@echo "  publish         Publish to PyPI (requires PYPI_TOKEN)."

install:
	@echo "Creating virtual environment with Python $(PYTHON_VERSION)..."
	@if [ ! -d .venv ]; then \
		$(UV) venv --python $(PYTHON_VERSION) 2>/dev/null || \
		$(UV) venv --python python$(PYTHON_VERSION) 2>/dev/null || \
		$(UV) venv --python 3.12 2>/dev/null || \
		$(UV) venv --python 3.13 2>/dev/null || \
		$(UV) venv; \
	fi
	@echo "Installing package and dependencies from pyproject.toml..."
	@$(UV) sync --extra dev

test: unit-test integration-test

unit-test:
	@$(PY) -m pytest tests/unit -q

integration-test:
	@$(PY) -m pytest tests/integration -q

test-cov: ## Run tests with coverage (HTML report)
	@$(PY) -m pytest tests/ --cov=laakhay/data --cov-report=html --cov-report=term -v

test-cov-xml: ## Run tests with coverage (XML report for CI)
	@$(PY) -m pytest tests/ --cov=laakhay/data --cov-report=xml --cov-report=term -v

test-cov-xml-unit: ## Run unit tests with coverage (XML report for CI)
	@$(PY) -m pytest tests/unit --cov=laakhay/data --cov-report=xml --cov-report=term -v

coverage: test-cov ## Run tests with coverage (alias)

lint:
	@$(PY) -m ruff check . 2>&1 || (echo "ruff check failed or not installed" && exit 1)

format:
	@$(PY) -m ruff format . 2>&1 || (echo "ruff format failed or not installed" && exit 1)

format-check:
	@$(PY) -m ruff format --check . 2>&1 || (echo "Code formatting issues found. Run 'make format' to fix." && exit 1)

type-check:
	@$(PY) -m mypy laakhay/data 2>&1 || (echo "mypy check failed or not installed" && exit 1)

fix:
	@$(PY) -m ruff check --fix . 2>&1 || (echo "ruff check --fix failed or not installed" && exit 1)
	@$(PY) -m ruff format . 2>&1 || (echo "ruff format failed or not installed" && exit 1)

clean:
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.pyc' -delete || true
	@find . -name '*.pyo' -delete || true
	@rm -rf .pytest_cache || true
	@rm -rf htmlcov || true
	@rm -rf .coverage || true
	@rm -rf dist || true
	@rm -rf build || true
	@rm -rf *.egg-info || true

build: clean
	@$(UV) sync --extra dev
	@$(UV) build

publish: build
	@$(UV) sync --extra dev
	@$(UV) run twine upload dist/*
