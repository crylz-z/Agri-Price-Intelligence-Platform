"""Data checks that gate publishing the clean layer. Errors fail the run."""

from datetime import date, timedelta
from statistics import median

import duckdb
import pyarrow as pa

KEY = "posting_date, region_id, market_name, commodity_name"
MIN_REGIONS = 15
MAX_POSTING_AGE_DAYS = 14
MIN_ROW_RATIO = 0.5
# shortcut: outliers are judged against the run's own commodity median; replace with
# per-commodity ceilings once 2 weeks of data exist.
OUTLIER_FACTOR = 10


def check(
    run: pa.Table,
    clean: pa.Table,
    today: date,
    prior_run_rows: list[int],
    window_full: bool,
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for this run's rows and the rebuilt clean rows."""
    con = duckdb.connect()
    con.register("run", run)
    con.register("clean", clean)

    def count(sql: str) -> int:
        row = con.sql(sql).fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    errors: list[str] = []
    warnings: list[str] = []

    if run.num_rows == 0:
        errors.append("0 rows scraped")

    if n := count(f"SELECT count(*) - count(DISTINCT ({KEY})) FROM clean"):
        errors.append(f"{n} duplicate keys in clean")
    nulls = " OR ".join(f"{c.strip()} IS NULL" for c in KEY.split(","))
    if n := count(f"SELECT count(*) FROM clean WHERE {nulls}"):
        errors.append(f"{n} clean rows with a null key column")
    if n := count("SELECT count(*) FROM clean WHERE price IS NULL OR price <= 0"):
        errors.append(f"{n} clean rows with price <= 0")

    oldest = today - timedelta(days=MAX_POSTING_AGE_DAYS)
    if n := count(
        "SELECT count(*) FROM run "
        f"WHERE posting_date > DATE '{today}' OR posting_date < DATE '{oldest}'"
    ):
        errors.append(f"{n} rows with posting_date outside {oldest}..{today}")

    regions = count("SELECT count(DISTINCT region_id) FROM run")
    if regions < MIN_REGIONS:
        errors.append(f"only {regions} regions scraped, need {MIN_REGIONS}")

    if prior_run_rows:
        floor = MIN_ROW_RATIO * median(prior_run_rows[-7:])
        if run.num_rows < floor:
            msg = f"{run.num_rows} rows is below 50% of the trailing 7-run median"
            (errors if window_full else warnings).append(msg)

    if n := count(
        "SELECT count(*) FROM clean JOIN ("
        "  SELECT commodity_name, median(price) AS med FROM clean GROUP BY 1"
        f") USING (commodity_name) WHERE price > {OUTLIER_FACTOR} * med"
    ):
        warnings.append(f"{n} price outliers above {OUTLIER_FACTOR}x commodity median")

    return errors, warnings
