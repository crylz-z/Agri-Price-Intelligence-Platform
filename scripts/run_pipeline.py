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

import requests

from src.core.logger import get_logger

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = ROOT / "src" / "etl" / "dbt_project"
PYTHON = sys.executable

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def send_discord_alert(message: str, status: str = "ERROR") -> None:
    """
    Posts a pipeline status notification to Discord via webhook.
    Silently no-ops if DISCORD_WEBHOOK_URL is not set (e.g. local dev).
    Never raises — alerting failure must not affect the pipeline exit code.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not set — skipping Discord notification.")
        return

    color = 65280 if status in ["SUCCESS", "INFO"] else 16711680  # green / red
    if status == "WARNING":
        color = 16776960  # yellow

    payload = {
        "embeds": [
            {
                "title": f"Agri-Price Pipeline — {status}",
                "description": message,
                "color": color,
            }
        ]
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Discord notification sent.", status=status)
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to send Discord notification.", error=str(exc))


def _run(cmd: list[str], cwd: Path | None = None, step_name: str = "") -> None:
    """
    Run a subprocess command with check=True so any non-zero exit raises
    subprocess.CalledProcessError, which is caught by the outer try/except.
    """
    label = step_name or " ".join(cmd)
    logger.info("Starting step.", step=label, cmd=" ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=os.environ, check=True)
    logger.info("Step completed.", step=label)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _load_dotenv()

    # Validate required env vars before doing any work.
    required = ["S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.critical(msg)
        send_discord_alert(f"Pipeline Failed: {msg}")
        sys.exit(1)

    logger.info("Starting ELT Pipeline...")
    send_discord_alert("Starting ELT Pipeline...", status="INFO")

    try:
        # ------------------------------------------------------------------
        # Step 0 — PREFLIGHT: Verify S3 connectivity.
        # ------------------------------------------------------------------
        _run(
            [PYTHON, "scripts/preflight_check.py"],
            cwd=ROOT,
            step_name="Preflight Check (S3 Connectivity)",
        )

        # ------------------------------------------------------------------
        # Step 1 — WRITE: Extract & load Bronze layer via dlt.
        # ------------------------------------------------------------------
        _run(
            [PYTHON, "-m", "src.etl.dlt_pipeline.agri_price_pipeline"],
            cwd=ROOT,
            step_name="dlt Extract & Load (Bronze)",
        )

        # ------------------------------------------------------------------
        # Step 2 — AUDIT + PUBLISH: dbt build runs models then tests.
        # check=True means a failing test raises CalledProcessError here,
        # preventing bad data from reaching the Gold layer.
        # ------------------------------------------------------------------
        os.chdir(DBT_PROJECT_DIR)

        _run(
            ["dbt", "deps"],
            step_name="dbt deps",
        )
        _run(
            ["dbt", "build", "--profiles-dir", str(DBT_PROJECT_DIR)],
            step_name="dbt build (Transform + Audit)",
        )

    except Exception as e:
        error_str = str(e)
        # Truncate to 1500 chars to fit Discord limits and include context
        trunc_err_str = (
            (error_str[:1500] + "...") if len(error_str) > 1500 else error_str
        )

        logger.critical("Pipeline failed.", error=trunc_err_str)
        # Add snippet markdown formatting for Discord readability
        send_discord_alert(f"Pipeline Failed:\n```\n{trunc_err_str}\n```")
        sys.exit(1)

    logger.info("ELT Pipeline completed successfully.")

    # Check for 0-row extraction via pipeline status file
    import tempfile
    import json

    status_file = os.path.join(tempfile.gettempdir(), "agri_pipeline_status.json")
    zero_rows = False
    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                stats = json.load(f)
                if stats.get("load_packages", 1) == 0:
                    zero_rows = True
        except Exception:
            pass

    if zero_rows:
        warning_msg = (
            "⚠️ **Pipeline Completed with 0 Rows Extracted**\n"
            "The pipeline executed fully, but no data was returned by the DA Bantay Presyo server. "
            "This confirms the government API is currently unreachable or blocking requests. "
            "Downstream data was untouched."
        )
        logger.warning(warning_msg)
        send_discord_alert(warning_msg, status="WARNING")
    else:
        send_discord_alert(
            "ELT Pipeline completed successfully. Bronze -> Silver -> Gold is healthy.",
            status="SUCCESS",
        )


if __name__ == "__main__":
    main()
