"""PSA OpenSTAT -> raw snapshots on R2 -> dbt build of the mart.

    uv run python -m src.etl.pipeline           # dbt runs if ingest wrote or a mart is stale
    uv run python -m src.etl.pipeline --build   # always run dbt (e.g. after a fix)

A failed dbt test skips the mart, so R2 keeps the last good one; the run exits 1.
The next run finds that mart older than the newest snapshot and builds again.
"""

import sys
from datetime import datetime
from pathlib import Path

from dbt.cli.main import dbtRunner
from dotenv import load_dotenv
from fsspec import AbstractFileSystem

from src.core import storage
from src.core.logger import get_logger
from src.etl import ingest

logger = get_logger(__name__)

DBT_DIR = str(Path(__file__).parents[2] / "dbt")
# The models in dbt/models/marts/; a pytest checks the two match.
MARTS = (
    "change_only_monthly",
    "farmer_share_monthly",
    "food_verdicts",
    "growth_since_2018",
    "price_changes_yearly",
    "seasonal_baseline",
)


def build() -> bool:
    args = ["build", "--project-dir", DBT_DIR, "--profiles-dir", DBT_DIR]
    return bool(dbtRunner().invoke(args).success)


def stale(fs: AbstractFileSystem, root: str, newest_snapshot: datetime | None) -> bool:
    """True when a mart is missing or older than the newest snapshot: one HEAD per mart."""
    if newest_snapshot is None:
        return False
    built = [storage.modified(fs, f"{root}/mart/{m}.parquet") for m in MARTS]
    return any(t is None or t < newest_snapshot for t in built)


def run(written: list[str], force: bool = False, is_stale: bool = False) -> bool:
    """Build the mart if ingest wrote a snapshot, a mart is stale, or forced.

    False on failure.
    """
    if not (written or force or is_stale):
        logger.info("No new release; dbt skipped.")
        return True
    if is_stale and not (written or force):
        logger.info("A mart is older than the newest snapshot; retrying dbt.")
    return build()


def main() -> None:
    load_dotenv()
    fs, root = storage.filesystem(), storage.root()
    force = "--build" in sys.argv[1:]
    with ingest.make_session() as session:
        result = ingest.run(session, fs, root)
    logger.info("Ingest finished.", snapshots_written=len(result.written))
    is_stale = not (result.written or force) and stale(fs, root, result.newest_kept)
    if not run(result.written, force=force, is_stale=is_stale):
        logger.error("dbt build failed; the mart on R2 was not replaced.")
        sys.exit(1)


if __name__ == "__main__":
    main()
