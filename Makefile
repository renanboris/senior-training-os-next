.PHONY: install install-dev test lint format

install:
	pip install -r requirements.txt
	python -m playwright install chromium

install-dev:
	pip install -r requirements-dev.txt
	python -m playwright install chromium

test:
	pytest

lint:
	ruff check .
	black --check .

format:
	black .
	ruff check . --fix
