.PHONY: help install lint test preflight run ui backfill

# ==============================================================================
# General
# ==============================================================================

# Display this help screen.
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Project Setup:"
	@echo "  install          Sync local virtual environment with uv.lock"
	@echo ""
	@echo "Quality Assurance:"
	@echo "  lint             Run formatter (Ruff) and linter checks"
	@echo "  test             Execute pytest suite"
	@echo ""
	@echo "Data Engineering & Operations:"
	@echo "  run              Execute full ELT pipeline (dL/dT/dS)"
	@echo "  backfill         Materialize/Repair layers. Usage: make backfill ARGS=\"2026-02-01 [end_date]\""
	@echo "  backfill-all     Perform a full historical backfill across all partitions"
	@echo "  preflight        Verify S3 and Discord connectivity"
	@echo ""
	@echo "Application:"
	@echo "  ui               Start the Streamlit dashboard"

# ==============================================================================
# Setup & Quality
# ==============================================================================

install:
	uv sync

lint:
	uv run ruff format
	uv run ruff check . --fix
	uv run pre-commit run --all-files

test:
	uv run pytest tests/

# ==============================================================================
# Data Pipeline & Operations
# ==============================================================================

preflight:
	uv run python scripts/preflight_check.py

run:
	uv run python scripts/run_pipeline.py

backfill:
	@echo "Repairing and materializing Silver/Gold layers..."
	uv run python scripts/manual_silver_gold_backfill.py $(ARGS)

backfill-all:
	@echo "Performing FULL historical backfill..."
	uv run python scripts/manual_silver_gold_backfill.py --all

ui:
	uv run streamlit run src/dashboard/app.py
