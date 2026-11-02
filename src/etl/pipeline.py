"""PSA OpenSTAT -> raw snapshots on R2 -> dbt build of the mart.

    uv run python -m src.etl.pipeline           # dbt runs only if ingest wrote
    uv run python -m src.etl.pipeline --build   # always run dbt (e.g. after a fix)

A failed dbt test skips the mart, so R2 keeps the last good one; the run exits 1.
"""

import sys
from pathlib import Path

from dbt.cli.main import dbtRunner
from dotenv import load_dotenv

from src.core import storage
from src.core.logger import get_logger
from src.etl import ingest

logger = get_logger(__name__)

DBT_DIR = str(Path(__file__).parents[2] / "dbt")


def build() -> bool:
    args = ["build", "--project-dir", DBT_DIR, "--profiles-dir", DBT_DIR]
    return bool(dbtRunner().invoke(args).success)


def run(written: list[str], force: bool = False) -> bool:
    """Build the mart if ingest wrote a snapshot (or if forced). False on failure."""
    if not (written or force):
        logger.info("No new release; dbt skipped.")
        return True
    return build()


def main() -> None:
    load_dotenv()
    with ingest.make_session() as session:
        written = ingest.run(session, storage.filesystem(), storage.root())
    logger.info("Ingest finished.", snapshots_written=len(written))
    if not run(written, force="--build" in sys.argv[1:]):
        logger.error("dbt build failed; the mart on R2 was not replaced.")
        sys.exit(1)


if __name__ == "__main__":
    main()
