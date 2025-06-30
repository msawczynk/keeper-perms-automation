.PHONY: help install install-dev test lint format clean run-template run-lint

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:  ## Install the package and dependencies
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev,ui]"
	pre-commit install

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=keeper_auto --cov-report=html --cov-report=term

lint:  ## Run linting checks
	flake8 keeper_auto tests
	mypy keeper_auto

format:  ## Format code with black
	black keeper_auto tests cli.py

check:  ## Run all checks (format, lint, test)
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test

clean:  ## Clean up temporary files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-template:  ## Generate a CSV template
	python cli.py template --force

run-lint:  ## Lint the default CSV template
	python -m keeper_auto.template --lint

run-apply:  ## Apply permissions from CSV (requires --csv argument)
	@echo "Usage: make run-apply CSV=path/to/file.csv"
	@if [ -z "$(CSV)" ]; then echo "Error: CSV argument required"; exit 1; fi
	python cli.py apply --csv $(CSV)

run-dry:  ## Dry run permissions from CSV (requires --csv argument)
	@echo "Usage: make run-dry CSV=path/to/file.csv"
	@if [ -z "$(CSV)" ]; then echo "Error: CSV argument required"; exit 1; fi
	python cli.py dry-run --csv $(CSV)

run-reconcile:  ## Reconcile permissions
	python cli.py reconcile 