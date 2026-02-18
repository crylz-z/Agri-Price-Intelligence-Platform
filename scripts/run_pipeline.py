"""
WAP (Write-Audit-Publish) Pipeline Orchestrator
================================================
Executes the full ELT pipeline in strict dependency order:

  1. Write   — dlt: extract from source, write Bronze Parquet to S3.
  2. Audit   — dbt build: transform Bronze → Silver/Gold, then run all
               data tests as a gatekeeper. If any test fails, the
               process exits non-zero and downstream consumers are
               never updated.
  3. Publish — implicit: Gold layer is now valid and queryable by the
               dashboard.

Usage (local):
    python scripts/run_pipeline.py

Usage (CI):
    python scripts/run_pipeline.py
    (AWS credentials are injected via OIDC; .env is not loaded in CI.)
"""

import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = ROOT / "src" / "etl" / "dbt_project"


def _load_dotenv() -> None:
    """Load .env into the current process environment (local dev only)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    with env_file.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _run(cmd: list[str], cwd: Path | None = None, step_name: str = "") -> None:
    """
    Run a subprocess command. Raises SystemExit(1) on non-zero return code.
    Streams stdout/stderr in real time so CI logs are not buffered.
    """
    label = step_name or " ".join(cmd)
    print(f"\n{'='*60}")
    print(f"STEP: {label}")
    print(f"CMD : {' '.join(cmd)}")
    if cwd:
        print(f"CWD : {cwd}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=cwd, env=os.environ)

    if result.returncode != 0:
        print(f"\n[FATAL] Step '{label}' failed with exit code {result.returncode}.")
        print("Pipeline halted. Downstream steps will NOT execute.")
        sys.exit(1)

    print(f"\n[OK] Step '{label}' completed successfully.")


def main() -> None:
    # Load .env for local development. In CI, env vars are injected by the runner.
    _load_dotenv()

    # Validate required env vars before doing any work.
    required = ["S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"[FATAL] Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1 — WRITE: Extract & load Bronze layer via dlt.
    # Uses 'uv run' to ensure the correct venv is active in any context.
    # ------------------------------------------------------------------
    _run(
        ["uv", "run", "python", "-m", "src.etl.dlt_pipeline.agri_price_pipeline"],
        cwd=ROOT,
        step_name="dlt Extract & Load (Bronze)",
    )

    # ------------------------------------------------------------------
    # Step 2 — AUDIT + PUBLISH: dbt build runs models then tests.
    # A single failing test aborts the build, preventing bad data from
    # reaching the Gold layer that the dashboard reads.
    # ------------------------------------------------------------------
    _run(
        ["dbt", "deps"],
        cwd=DBT_PROJECT_DIR,
        step_name="dbt deps",
    )
    _run(
        ["dbt", "build", "--profiles-dir", str(DBT_PROJECT_DIR)],
        cwd=DBT_PROJECT_DIR,
        step_name="dbt build (Transform + Audit)",
    )

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE — All steps passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
