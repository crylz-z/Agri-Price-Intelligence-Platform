"""Ingest PSA OpenSTAT retail price tables as raw snapshots, one per release.

1 GET lists the tables with PSA's `updated` time. A table is downloaded only when
its snapshot `raw/table=<id>/updated=<YYYYMMDDTHHMMSS>.csv` is missing, so a run
with no new release costs that GET plus 1 HEAD per table (Class B) and never lists
R2. Snapshots are stored as returned (Windows-1252 CSV) and never rewritten.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version

import requests
from fsspec import AbstractFileSystem
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core import storage
from src.core.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M/2018NEW"
# An empty query returns the whole table; it is not capped by `maxValues`.
CSV_QUERY = {"query": [], "response": {"format": "csv"}}
CSV_HEADER = b'"Geolocation","Commodity",'
USER_AGENT = (
    f"apip/{version('agri-price-intelligence-platform')} "
    "(+https://github.com/crylz-z/Agri-Price-Intelligence-Platform)"
)
TIMEOUT_SECONDS = 60
REQUEST_DELAY_SECONDS = 1.0


@dataclass(frozen=True)
class Table:
    id: str  # "0042M4ARN01", without PSA's ".px"
    updated: str  # PSA's release time, "20261002T081513"


def make_session() -> requests.Session:
    # Honest bot: Cloudflare 403s a bare client but serves the named UA.
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session


def list_tables(session: requests.Session) -> list[Table]:
    response = session.get(f"{BASE_URL}/", timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return [
        Table(
            id=t["id"].removesuffix(".px"),
            updated=datetime.fromisoformat(t["updated"]).strftime("%Y%m%dT%H%M%S"),
        )
        for t in response.json()
        if t["type"] == "t"
    ]


def snapshot_path(root: str, table: Table) -> str:
    return f"{root}/raw/table={table.id}/updated={table.updated}.csv"


def download(session: requests.Session, table: Table) -> bytes:
    response = session.post(
        f"{BASE_URL}/{table.id}.px", json=CSV_QUERY, timeout=TIMEOUT_SECONDS
    )
    response.raise_for_status()
    # A snapshot is immutable, so never store an error or challenge page as one.
    if not response.content.startswith(CSV_HEADER):
        raise ValueError(f"{table.id}: not a PSA price CSV: {response.content[:80]!r}")
    return response.content


def run(
    session: requests.Session,
    fs: AbstractFileSystem,
    root: str,
    delay: float = REQUEST_DELAY_SECONDS,
) -> list[str]:
    """Write a snapshot for each table PSA has re-released. Returns the paths written."""
    written = []
    for table in list_tables(session):
        path = snapshot_path(root, table)
        if storage.exists(fs, path):
            continue
        time.sleep(delay)
        fs.pipe_file(path, download(session, table))
        logger.info("Wrote snapshot.", path=path)
        written.append(path)
    return written
