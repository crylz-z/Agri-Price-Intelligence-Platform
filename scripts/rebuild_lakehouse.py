"""
Manual Lakehouse Rebuild — Silver & Gold Only
=============================================
Use this when Bronze data already exists in S3 but the Silver/Gold
layers are missing or stale (e.g., a pipeline run failed mid-way,
or you need to re-process a specific day without re-scraping).

This script SKIPS the dlt extraction step entirely.
It runs only: dbt deps → dbt build (transform + audit).

Usage:
    python scripts/rebuild_lakehouse.py
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = ROOT / "src" / "etl" / "dbt_project"
PYTHON = sys.executable


def _load_dotenv() -> None:
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
    label = step_name or " ".join(cmd)
    print(f"\n{'='*60}")
    print(f"STEP: {label}")
    print(f"CMD : {' '.join(cmd)}")
    if cwd:
        print(f"CWD : {cwd}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=cwd, env=os.environ)

    if result.returncode != 0:
        print(f"\n[FATAL] '{label}' failed (exit {result.returncode}). Halting.")
        sys.exit(1)

    print(f"\n[OK] '{label}' completed.")


def main() -> None:
    print("=" * 60)
    print("MANUAL LAKEHOUSE REBUILD — Silver & Gold Only")
    print("Bronze extraction (dlt) is SKIPPED.")
    print("Assumes Bronze Parquet files already exist in S3.")
    print("=" * 60)

    _load_dotenv()

    required = ["S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"[FATAL] Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    _run(["dbt", "deps"], cwd=DBT_PROJECT_DIR, step_name="dbt deps")
    _run(
        ["dbt", "build", "--profiles-dir", str(DBT_PROJECT_DIR)],
        cwd=DBT_PROJECT_DIR,
        step_name="dbt build (Silver + Gold + Audit)",
    )

    print("\n" + "=" * 60)
    print("REBUILD COMPLETE — Dashboard data is now refreshed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
