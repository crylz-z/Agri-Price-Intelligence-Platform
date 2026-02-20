.PHONY: install lint test run preflight

# ==============================================================================
# Dependency Management
# ==============================================================================

# Syncs the local virtual environment with uv.lock. Run this after pulling new changes.
install:
	uv sync

# ==============================================================================
# Quality Assurance
# ==============================================================================

# Runs the formatter, linter, and all pre-commit hooks to ensure code quality.
lint:
	uv run ruff format
	uv run ruff check . --fix
	uv run pre-commit run --all-files

# Executes the Pytest suite (unit and integration tests).
test:
	uv run pytest tests/

# ==============================================================================
# Execution & Operations
# ==============================================================================

# Executes the full ELT pipeline: dlt extraction, dbt transformation, and audit gate.
run:
	uv run python scripts/run_pipeline.py

# Verifies S3 connection and Discord alerting health before running a pipeline.
preflight:
	uv run python scripts/preflight_check.py
