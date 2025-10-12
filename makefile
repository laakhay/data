SHELL := /bin/sh

# Configurable Python executable - use venv if available
PY ?= $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: help install test unit integration e2e lint format fix coverage clean build publish

help:
	@echo "Make targets:"
	@echo "  install     Install project and optional requirements.*."
	@echo "  test        Run unit tests (alias for 'unit')."
	@echo "  unit        Run unit test suite (tests/unit)."
	@echo "  integration Run integration tests (tests/integration)."
	@echo "  e2e         Run end-to-end tests (tests/e2e)."
	@echo "  lint        Run ruff lint if available."
	@echo "  format      Run ruff format/black if available."
	@echo "  fix         Auto-fix linting issues and format code."
	@echo "  coverage    Run tests with coverage report."
	@echo "  clean       Remove caches and compiled artifacts."
	@echo "  build       Build distribution packages."
	@echo "  publish     Publish to PyPI (requires PYPI_TOKEN)."

install:
	@$(PY) -m pip install -U pip setuptools wheel
	@if [ -s requirements.txt ]; then \
		$(PY) -m pip install -r requirements.txt; \
	else \
		echo "requirements.txt empty or missing; skipping"; \
	fi
	@if [ -s requirements.dev.txt ]; then \
		$(PY) -m pip install -r requirements.dev.txt; \
	else \
		echo "requirements.dev.txt empty or missing; skipping"; \
	fi
	@$(PY) -m pip install -e .

test: unit

unit:
	@$(PY) -m pytest -q tests/unit

integration:
	@$(PY) -m pytest -q tests/integration

e2e:
	@$(PY) -m pytest -q tests/e2e

coverage:
	@$(PY) -m pytest tests/ --cov=laakhay/data --cov-report=html --cov-report=term

lint:
	@command -v ruff >/dev/null 2>&1 && ruff check . || echo "ruff not installed; skipping lint"

format:
	@command -v ruff >/dev/null 2>&1 && ruff format . || true
	@command -v black >/dev/null 2>&1 && black . || echo "formatters not installed; skipping black"

fix:
	@command -v ruff >/dev/null 2>&1 && ruff check --fix . || echo "ruff not installed; skipping ruff fix"
	@command -v ruff >/dev/null 2>&1 && ruff format . || true
	@command -v black >/dev/null 2>&1 && black . || echo "formatters not installed; skipping black"

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
	@$(PY) -m pip install --upgrade build
	@$(PY) -m build --sdist --wheel

publish: build
	@$(PY) -m pip install --upgrade twine
	@$(PY) -m twine upload dist/*
