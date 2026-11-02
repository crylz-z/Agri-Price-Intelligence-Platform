"""Read-only SQL over the lake, for checks and analysis.

    uv run python -m src.etl.query "SELECT region_name, max(posting_date) FROM raw GROUP BY 1"

Views: `raw` (every run, plus `scrape_date` and `run` from the path) and `clean`.
Each view the query names lists its prefix (1 Class A op on R2), so run queries by
hand, never in a loop.
"""

import re
import sys
from collections.abc import Iterable

import duckdb
from dotenv import load_dotenv

from src.core import storage

READ_ONLY = ("SELECT", "WITH", "DESCRIBE", "SUMMARIZE", "FROM")
GLOBS = {
    "raw": "raw/scrape_date=*/run=*.parquet",
    "clean": "clean/posting_date=*/prices.parquet",
}
# run=HHMMSS is a file name, not a folder, so hive partitioning skips it.
EXTRA = {"raw": ", regexp_extract(filename, 'run=(\\d+)', 1) AS run", "clean": ""}


def connect(root: str, names: Iterable[str] = GLOBS) -> duckdb.DuckDBPyConnection:
    """Views bind (and list their prefix) when created, so create only `names`."""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'Asia/Manila'")
    if root.startswith("s3://"):
        storage.configure_duckdb(con)
    for name in names:
        glob = GLOBS[name]
        con.execute(
            f"CREATE VIEW {name} AS SELECT * EXCLUDE (filename){EXTRA[name]} "
            f"FROM read_parquet('{root}/{glob}', hive_partitioning=true, filename=true)"
        )
    return con


def check_read_only(sql: str) -> None:
    words = sql.split(maxsplit=1)
    if not words or words[0].upper() not in READ_ONLY:
        raise ValueError(f"read-only: start the query with one of {READ_ONLY}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    check_read_only(sys.argv[1])
    load_dotenv()
    sql = sys.argv[1]
    used = [n for n in GLOBS if re.search(rf"\b{n}\b", sql, re.IGNORECASE)]
    con = connect(storage.root(), used)  # keep a reference: .show() needs it open
    con.sql(sql).show(max_rows=100)


if __name__ == "__main__":
    main()
