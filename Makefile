.PHONY: install dev test test-cov lint format typecheck clean check

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest repoTests/tests/ -v

test-cov:
	pytest repoTests/tests/ --cov=metzuda --cov-report=term-missing

lint:
	ruff check metzuda/ repoTests/tests/

format:
	ruff format metzuda/ repoTests/tests/

typecheck:
	mypy metzuda/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# Roda tudo antes de commitar
check: format lint typecheck test
