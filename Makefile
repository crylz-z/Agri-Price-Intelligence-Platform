.PHONY: install lint test preflight run

# ==============================================================================
# Dependency Management
# ==============================================================================

# Setup environment. Syncs the local virtual environment with uv.lock. Run this after pulling new changes.
install:
	uv sync

# ==============================================================================
# Quality Assurance
# ==============================================================================

# Formatting/Hygiene. Runs the formatter, linter, and all pre-commit hooks to ensure code quality.
lint:
	uv run ruff format
	uv run ruff check . --fix
	uv run pre-commit run --all-files

# Run pytest tests. Executes the Pytest suite (unit and integration tests).
test:
	uv run pytest tests/

# ==============================================================================
# Execution & Operations
# ==============================================================================

# Run preflight tests. Verifies S3 connection and Discord alerting health before running a pipeline.
preflight:
	uv run python scripts/preflight_check.py

# Run pipeline. Executes the full ELT pipeline: dlt extraction, dbt transformation, and audit gate.
run:
	uv run python scripts/run_pipeline.py

# Run Streamlit dashboard. Starts the local server for the web application.
ui:
	uv run streamlit run src/dashboard/app.py
