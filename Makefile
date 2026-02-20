.PHONY: install lint test run

install:
	uv sync

lint:
	uv run ruff format
	uv run ruff check . --fix
	uv run pre-commit run --all-files

test:
	uv run pytest

run:
	uv run python scripts/run_pipeline.py
