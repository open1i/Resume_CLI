.PHONY: install install-dev lint format type-check test clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

type-check:
	mypy resume_cli

test:
	pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete 2>/dev/null; true
	rm -rf .mypy_cache .ruff_cache .pytest_cache dist build *.egg-info
