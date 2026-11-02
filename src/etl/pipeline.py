"""Scrape -> raw -> clean, with checks before publish.

    uv run python -m src.etl.pipeline

Raw is written first and never changed. Clean is rebuilt only for the posting
dates this run touched, and only published when every check passes.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from dotenv import load_dotenv
from fsspec import AbstractFileSystem

from src.core import storage
from src.core.logger import get_logger
from src.etl import checks
from src.etl.scraper import PHT, make_session, scrape

logger = get_logger(__name__)

CLEAN_SQL = (Path(__file__).parents[2] / "sql" / "clean.sql").read_text()
WINDOW_DAYS = checks.MAX_POSTING_AGE_DAYS
RAW_SCHEMA = pa.schema(
    [
        ("extract_dt", pa.timestamp("us", tz="Asia/Manila")),
        ("region_id", pa.string()),
        ("region_name", pa.string()),
        ("market_name", pa.string()),
        ("commodity_group", pa.string()),
        ("commodity_name", pa.string()),
        ("specifications", pa.string()),
        ("price", pa.float64()),
        ("raw_date_text", pa.string()),
        ("posting_date", pa.date32()),
    ]
)


class ChecksFailed(Exception):
    pass


def to_table(records: list[dict[str, Any]]) -> pa.Table:
    return pa.Table.from_pylist(records, schema=RAW_SCHEMA)


def _scrape_date(path: str) -> date:
    return date.fromisoformat(path.split("scrape_date=")[1][:10])


def _raw_paths(fs: AbstractFileSystem, root: str, oldest: date) -> list[str]:
    # One flat, paginated ListObjectsV2 (1 Class A op per 1000 objects). glob() would
    # list each scrape_date= prefix separately. shortcut: lists all of raw/, switch to
    # per-day keys if raw/ passes ~5000 objects.
    paths = fs.find(f"{root}/raw")
    return sorted(
        p for p in paths if p.endswith(".parquet") and _scrape_date(p) >= oldest
    )


def _read(fs: AbstractFileSystem, path: str) -> pa.Table:
    with fs.open(path, "rb") as f:
        return pq.read_table(f)


def _write(fs: AbstractFileSystem, path: str, table: pa.Table) -> None:
    with fs.open(path, "wb") as f:
        pq.write_table(table, f)


def build_clean(raw: pa.Table, run: pa.Table) -> pa.Table:
    con = duckdb.connect()
    con.execute("SET TimeZone = 'Asia/Manila'")
    con.register("raw", raw)
    con.register("run", run)
    return con.sql(CLEAN_SQL).fetch_arrow_table()


def run(
    fs: AbstractFileSystem, root: str, records: list[dict[str, Any]], now: datetime
) -> list[str]:
    """Write raw, rebuild touched clean partitions, check, publish. Returns warnings."""
    if not records:
        raise ChecksFailed("0 rows scraped")
    today = now.astimezone(PHT).date()

    run_table = to_table(records)
    # A stale region rebuilds an old posting date, so read back to that date: rows for
    # posting date D can only sit in scrape dates >= D. Otherwise the rebuild would
    # drop other regions' rows for D.
    oldest_posted: date = pc.min(run_table["posting_date"]).as_py()
    oldest = min(today - timedelta(days=WINDOW_DAYS), oldest_posted)
    prior_paths = _raw_paths(fs, root, oldest)
    _write(fs, f"{root}/raw/scrape_date={today}/run={now:%H%M%S}.parquet", run_table)

    prior = [_read(fs, p) for p in prior_paths]
    raw = pa.concat_tables([*prior, run_table], promote_options="default")
    clean = build_clean(raw, run_table)

    errors, warnings = checks.check(
        run_table,
        clean,
        today,
        prior_run_rows=[t.num_rows for t in prior],
        window_full=len({_scrape_date(p) for p in prior_paths}) >= WINDOW_DAYS,
    )
    for w in warnings:
        logger.warning("Check warning.", detail=w)
    if errors:
        raise ChecksFailed("; ".join(errors))

    for posting_date in pc.unique(run_table["posting_date"]).to_pylist():
        partition = clean.filter(pc.equal(clean["posting_date"], posting_date))
        _write(
            fs, f"{root}/clean/posting_date={posting_date}/prices.parquet", partition
        )
    logger.info("Published clean.", rows=clean.num_rows, warnings=len(warnings))
    return warnings


def main() -> None:
    load_dotenv()
    now = datetime.now(PHT)
    with make_session() as session:
        result = scrape(session)
    logger.info(
        "Scrape finished.", rows=len(result.records), failures=len(result.failures)
    )
    for failure in result.failures:
        logger.warning("Scrape failure.", detail=failure)
    try:
        run(storage.filesystem(), storage.root(), result.records, now)
    except ChecksFailed as e:
        logger.error("Checks failed; clean not published.", errors=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
