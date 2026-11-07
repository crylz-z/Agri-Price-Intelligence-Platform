"""Ingest PSA OpenSTAT price tables as raw snapshots, one per release.

Every retail table (folder `2018NEW`) and the farmgate tables in `FARMGATE_TABLES`
(folder `NFG`). 1 GET per folder lists its tables with PSA's `updated` time. A table
is downloaded only when its snapshot `raw/table=<id>/updated=<YYYYMMDDTHHMMSS>.csv`
is missing, so a run with no new release costs those 2 GETs plus 1 HEAD per table
(Class B) and never lists R2. Snapshots are stored as returned (Windows-1252 CSV)
and never rewritten.
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

BASE_URL = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M"
RETAIL = "2018NEW"
FARMGATE = "NFG"
# An empty query returns the whole table; it is not capped by `maxValues`.
CSV_QUERY = {"query": [], "response": {"format": "csv"}}
# The first CSV columns of every retail table.
CSV_HEADER = b'"Geolocation","Commodity",'
# The farmgate tables the farmer's share uses (dbt/seeds/psa_farmgate_tables.csv),
# each with its own first columns: PSA lays them out differently.
FARMGATE_TABLES = {
    "0032M4AFN01": CSV_HEADER,  # Cereals
    "0032M4AFN02": CSV_HEADER,  # Rootcrops
    "0032M4AFN03": CSV_HEADER,  # Beans and Legumes
    "0032M4AFN04": CSV_HEADER,  # Condiments
    "0032M4AFN05": CSV_HEADER,  # Fruit Vegetables
    "0032M4AFN06": CSV_HEADER,  # Leafy Vegetables
    "0032M4AFN11": b'"Geolocation","Type",',  # Livestock and Poultry (Establishment)
    "0142M4EFGP0": b'"Commodity","Geolocation",',  # Major Crops
}
USER_AGENT = (
    f"ph-food-prices/{version('ph-food-prices')} "
    "(+https://github.com/crylz-z/ph-food-prices)"
)
TIMEOUT_SECONDS = 60
REQUEST_DELAY_SECONDS = 1.0


@dataclass(frozen=True)
class Table:
    folder: str  # RETAIL or FARMGATE
    id: str  # "0042M4ARN01", without PSA's ".px"
    updated: str  # PSA's release time, "20261002T081513"

    @property
    def header(self) -> bytes:
        """The bytes a real CSV of this table starts with."""
        return FARMGATE_TABLES[self.id] if self.folder == FARMGATE else CSV_HEADER


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


def list_tables(session: requests.Session, folder: str) -> list[Table]:
    """Every table in RETAIL; only FARMGATE_TABLES in FARMGATE."""
    response = session.get(f"{BASE_URL}/{folder}/", timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    tables = [
        Table(
            folder=folder,
            id=t["id"].removesuffix(".px"),
            updated=datetime.fromisoformat(t["updated"]).strftime("%Y%m%dT%H%M%S"),
        )
        for t in response.json()
        if t["type"] == "t"
    ]
    if folder == FARMGATE:
        tables = [t for t in tables if t.id in FARMGATE_TABLES]
    return tables


def snapshot_path(root: str, table: Table) -> str:
    return f"{root}/raw/table={table.id}/updated={table.updated}.csv"


def download(session: requests.Session, table: Table) -> bytes:
    response = session.post(
        f"{BASE_URL}/{table.folder}/{table.id}.px",
        json=CSV_QUERY,
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    # A snapshot is immutable, so never store an error or challenge page as one.
    if not response.content.startswith(table.header):
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
    tables = [t for folder in (RETAIL, FARMGATE) for t in list_tables(session, folder)]
    for table in tables:
        path = snapshot_path(root, table)
        if storage.exists(fs, path):
            continue
        time.sleep(delay)
        fs.pipe_file(path, download(session, table))
        logger.info("Wrote snapshot.", path=path)
        written.append(path)
    return written
