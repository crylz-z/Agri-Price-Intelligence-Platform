.PHONY: install lint test run preflight rebuild backfill

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
	uv run pytest

# ==============================================================================
# Execution & Operations
# ==============================================================================

# Executes the full ELT pipeline: dlt extraction, dbt transformation, and audit gate.
run:
	uv run python scripts/run_pipeline.py

# Verifies S3 connection and Discord alerting health before running a pipeline.
preflight:
	uv run python scripts/preflight_check.py

# Skips the extraction (dlt) phase and triggers dbt to rebuild Silver and Gold layers.
# Useful if the pipeline failed downstream or for regenerating analytical logic.
rebuild:
	uv run python scripts/rebuild_lakehouse.py

# Triggers a manual bypass operation to inject Bronze historic CSVs directly into Parquet.
backfill:
	uv run python scripts/backfill_lakehouse.py
