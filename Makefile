.PHONY: test build publish install-dev clean

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

test-coverage:
	pytest tests/ --cov=metzuda --cov-report=term-missing --cov-report=html

lint:
	ruff check metzuda/ tests/
	ruff format --check metzuda/ tests/

build:
	python -m build

publish-test:
	twine upload --repository testpypi dist/*

publish:
	twine upload dist/*

clean:
	rm -rf dist/ build/ *.egg-info/ htmlcov/ .coverage
