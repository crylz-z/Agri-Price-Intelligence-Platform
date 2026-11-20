from pathlib import Path
from typing import Any

import pytest
import requests
import s3fs
from fsspec.implementations.local import LocalFileSystem

from src.core import storage
from src.etl import ingest

FIXTURE = (Path(__file__).parent / "fixtures" / "psa_condiments.csv").read_bytes()
LISTING = [
    {"id": "0042M4ARN01.px", "type": "t", "updated": "2026-10-02T08:15:13"},
    {"id": "0042M4ARN04.px", "type": "t", "updated": "2026-10-02T08:15:49"},
    {"id": "old", "type": "l", "updated": "2020-01-01T00:00:00"},
]
# The 4 farmgate layouts (first CSV columns as PSA returned them on 2026-11-07;
# fish, quarterly, on 2026-11-11), and a farmgate table we don't use.
FARMGATE_LISTING = [
    {"id": "0032M4AFN01.px", "type": "t", "updated": "2026-10-30T10:06:08"},
    {"id": "0032M4AFN08.px", "type": "t", "updated": "2026-08-28T14:43:36"},
    {"id": "0032M4AFN11.px", "type": "t", "updated": "2026-11-06T10:50:35"},
    {"id": "0142M4EFGP0.px", "type": "t", "updated": "2026-11-06T08:15:46"},
    {"id": "0152M4GFPF0.px", "type": "t", "updated": "2026-11-06T13:19:46"},
]
FARMGATE_CSV = {
    "0032M4AFN01": b'"Geolocation","Commodity","2010 January"\r\n',
    "0032M4AFN11": b'"Geolocation","Type","2010 January"\r\n',
    "0142M4EFGP0": b'"Commodity","Geolocation","2010 January"\r\n',
    "0152M4GFPF0": b'"Geolocation","Species","2002 Quarter 1"\r\n',
}
# The CPI folder holds a dozen tables; only the one in CPI_TABLES is kept.
CPI_LISTING = [
    {"id": "0012M4ACP22.px", "type": "t", "updated": "2026-11-05T08:35:53"},
    {"id": "0012M4ACP23.px", "type": "t", "updated": "2026-11-05T08:35:53"},
]
CPI_CSV = b'"Geolocation","Commodity Description","2018 Jan"\r\n'
# The wholesale folder holds 10 tables; fruits (AWB07) and fish (AWB10) are kept,
# commercial crops (AWB08) is not.
WHOLESALE_LISTING = [
    {"id": f"0052M4AWB{n:02}.px", "type": "t", "updated": "2026-11-04T08:31:39"}
    for n in range(1, 11)
]
WHOLESALE_CSV = b'"Geolocation","Commodity","2010 January"\r\n'


class FakeResponse:
    def __init__(self, content: bytes = b"", json: Any = None) -> None:
        self.content, self._json = content, json

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Any:
        return self._json


class FakeSession:
    """Retail `listing` and `csv`; farmgate `farmgate` listing and `farmgate_csv`."""

    def __init__(
        self,
        listing: list[dict[str, str]],
        csv: bytes = FIXTURE,
        farmgate: list[dict[str, str]] | None = None,
        farmgate_csv: dict[str, bytes] = FARMGATE_CSV,
        cpi: list[dict[str, str]] | None = None,
        cpi_csv: bytes = CPI_CSV,
        wholesale: list[dict[str, str]] | None = None,
    ) -> None:
        self.listings = {
            ingest.RETAIL: listing,
            ingest.FARMGATE: farmgate or [],
            ingest.CPI: cpi or [],
            ingest.WHOLESALE: wholesale or [],
        }
        self.csv, self.farmgate_csv, self.cpi_csv = csv, farmgate_csv, cpi_csv
        self.posts: list[str] = []
        self.queries: dict[str, Any] = {}

    def get(self, url: str, **_: Any) -> FakeResponse:
        folder = url.removeprefix(f"{ingest.BASE_URL}/").removesuffix("/")
        return FakeResponse(json=self.listings[folder])

    def post(self, url: str, json: Any, **_: Any) -> FakeResponse:
        folder, _, name = url.removeprefix(f"{ingest.BASE_URL}/").rpartition("/")
        self.posts.append(name)
        self.queries[name] = json
        if folder == ingest.CPI:
            return FakeResponse(content=self.cpi_csv)
        assert json == ingest.CSV_QUERY
        if folder == ingest.RETAIL:
            return FakeResponse(content=self.csv)
        if folder == ingest.WHOLESALE:
            return FakeResponse(content=WHOLESALE_CSV)
        return FakeResponse(content=self.farmgate_csv[name.removesuffix(".px")])


@pytest.fixture
def lake(tmp_path):
    return LocalFileSystem(auto_mkdir=True), tmp_path.as_posix()


def test_list_tables_keeps_tables_and_compacts_updated():
    assert ingest.list_tables(FakeSession(LISTING), ingest.RETAIL) == [
        ingest.Table(ingest.RETAIL, "0042M4ARN01", "20261002T081513"),
        ingest.Table(ingest.RETAIL, "0042M4ARN04", "20261002T081549"),
    ]


def test_farmgate_listing_keeps_only_the_tables_we_use():
    session = FakeSession(LISTING, farmgate=FARMGATE_LISTING)
    ids = [t.id for t in ingest.list_tables(session, ingest.FARMGATE)]
    assert ids == ["0032M4AFN01", "0032M4AFN11", "0142M4EFGP0", "0152M4GFPF0"]


def test_farmgate_tables_match_the_dbt_seed():
    seed = Path(__file__).parents[1] / "dbt" / "seeds" / "psa_farmgate_tables.csv"
    ids = [line.split(",")[0] for line in seed.read_text().splitlines()[1:]]
    assert ids == list(ingest.FARMGATE_TABLES)


def test_wholesale_listing_keeps_only_the_tables_we_use():
    session = FakeSession(LISTING, wholesale=WHOLESALE_LISTING)
    ids = [t.id for t in ingest.list_tables(session, ingest.WHOLESALE)]
    assert ids == [f"0052M4AWB{n:02}" for n in (1, 2, 3, 4, 5, 6, 7, 9, 10)]


def test_wholesale_tables_match_the_dbt_seed():
    seed = Path(__file__).parents[1] / "dbt" / "seeds" / "psa_wholesale_tables.csv"
    ids = [line.split(",")[0] for line in seed.read_text().splitlines()[1:]]
    assert ids == list(ingest.WHOLESALE_TABLES)


def test_wholesale_snapshots_are_written(lake):
    fs, root = lake
    session = FakeSession([], wholesale=WHOLESALE_LISTING)
    written = ingest.run(session, fs, root, delay=0)

    assert len(written) == len(ingest.WHOLESALE_TABLES)
    assert fs.cat_file(written[0]) == WHOLESALE_CSV


def test_cpi_tables_match_the_dbt_seed():
    seed = Path(__file__).parents[1] / "dbt" / "seeds" / "psa_cpi_tables.csv"
    ids = [line.split(",")[0] for line in seed.read_text().splitlines()[1:]]
    assert ids == list(ingest.CPI_TABLES)


def test_cpi_asks_only_for_the_national_rows_of_a_few_groups(lake):
    fs, root = lake
    session = FakeSession([], cpi=CPI_LISTING)
    written = ingest.run(session, fs, root, delay=0)

    assert written == [f"{root}/raw/table=0012M4ACP22/updated=20261105T083553.csv"]
    assert session.queries == {"0012M4ACP22.px": ingest.CPI_QUERY}
    assert fs.cat_file(written[0]) == CPI_CSV


def test_cpi_refuses_a_retail_layout(lake):
    fs, root = lake
    session = FakeSession([], cpi=CPI_LISTING[:1], cpi_csv=FIXTURE)
    with pytest.raises(ValueError, match="0012M4ACP22: not a PSA price CSV"):
        ingest.run(session, fs, root, delay=0)
    assert not fs.exists(f"{root}/raw")


def test_farmgate_snapshots_are_written_with_each_tables_header(lake):
    fs, root = lake
    session = FakeSession([], farmgate=FARMGATE_LISTING)
    written = ingest.run(session, fs, root, delay=0)

    assert written == [
        f"{root}/raw/table=0032M4AFN01/updated=20261030T100608.csv",
        f"{root}/raw/table=0032M4AFN11/updated=20261106T105035.csv",
        f"{root}/raw/table=0142M4EFGP0/updated=20261106T081546.csv",
        f"{root}/raw/table=0152M4GFPF0/updated=20261106T131946.csv",
    ]
    assert session.posts == [
        "0032M4AFN01.px",
        "0032M4AFN11.px",
        "0142M4EFGP0.px",
        "0152M4GFPF0.px",
    ]
    assert [fs.cat_file(p) for p in written] == list(FARMGATE_CSV.values())
    assert (
        ingest.run(FakeSession([], farmgate=FARMGATE_LISTING), fs, root, delay=0) == []
    )


@pytest.mark.parametrize("table_id", list(FARMGATE_CSV))
def test_farmgate_table_refuses_another_tables_layout(lake, table_id):
    """Each farmgate table checks its own header, not the retail one."""
    fs, root = lake
    listing = [t for t in FARMGATE_LISTING if t["id"] == f"{table_id}.px"]
    wrong = next(v for k, v in FARMGATE_CSV.items() if k != table_id)
    session = FakeSession([], farmgate=listing, farmgate_csv={table_id: wrong})
    with pytest.raises(ValueError, match=f"{table_id}: not a PSA price CSV"):
        ingest.run(session, fs, root, delay=0)
    assert not fs.exists(f"{root}/raw")


def test_first_run_writes_one_snapshot_per_table_as_returned(lake):
    fs, root = lake
    session = FakeSession(LISTING)
    written = ingest.run(session, fs, root, delay=0)

    assert written == [
        f"{root}/raw/table=0042M4ARN01/updated=20261002T081513.csv",
        f"{root}/raw/table=0042M4ARN04/updated=20261002T081549.csv",
    ]
    assert session.posts == ["0042M4ARN01.px", "0042M4ARN04.px"]
    assert all(fs.cat_file(p) == FIXTURE for p in written)


def test_unchanged_release_downloads_nothing(lake):
    fs, root = lake
    ingest.run(FakeSession(LISTING), fs, root, delay=0)
    session = FakeSession(LISTING)
    assert ingest.run(session, fs, root, delay=0) == []
    assert session.posts == []


def test_new_release_adds_a_snapshot_and_keeps_the_old_one(lake):
    fs, root = lake
    ingest.run(FakeSession(LISTING), fs, root, delay=0)
    revised = [{**LISTING[1], "updated": "2026-11-04T09:00:00"}]
    session = FakeSession(revised)

    written = ingest.run(session, fs, root, delay=0)
    assert written == [f"{root}/raw/table=0042M4ARN04/updated=20261104T090000.csv"]
    assert len(fs.ls(f"{root}/raw/table=0042M4ARN04")) == 2


def test_non_csv_response_is_never_stored(lake):
    fs, root = lake
    page = b"<!DOCTYPE html><title>Just a moment...</title>"
    with pytest.raises(ValueError, match="not a PSA price CSV"):
        ingest.run(FakeSession(LISTING, csv=page), fs, root, delay=0)
    assert not fs.exists(f"{root}/raw")


def test_s3_exists_is_one_head_and_never_lists(monkeypatch):
    fs = s3fs.S3FileSystem(anon=True, skip_instance_cache=True)
    calls: list[tuple[str, dict[str, str]]] = []

    def call_s3(method: str, **kwargs: str) -> dict[str, str]:
        calls.append((method, kwargs))
        if kwargs["Key"].endswith("missing.csv"):
            raise FileNotFoundError(kwargs["Key"])
        return {}

    monkeypatch.setattr(fs, "call_s3", call_s3)
    assert storage.exists(fs, "s3://bucket/raw/table=A/updated=1.csv")
    assert not storage.exists(fs, "s3://bucket/raw/table=A/missing.csv")
    assert calls == [
        ("head_object", {"Bucket": "bucket", "Key": "raw/table=A/updated=1.csv"}),
        ("head_object", {"Bucket": "bucket", "Key": "raw/table=A/missing.csv"}),
    ]


def test_session_names_itself():
    ua = ingest.make_session().headers["User-Agent"]
    assert isinstance(ua, str) and ua.startswith("ph-food-prices/")
    assert isinstance(ingest.make_session(), requests.Session)
