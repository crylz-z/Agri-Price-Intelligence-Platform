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


class FakeResponse:
    def __init__(self, content: bytes = b"", json: Any = None) -> None:
        self.content, self._json = content, json

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Any:
        return self._json


class FakeSession:
    def __init__(self, listing: list[dict[str, str]], csv: bytes = FIXTURE) -> None:
        self.listing, self.csv = listing, csv
        self.posts: list[str] = []

    def get(self, url: str, **_: Any) -> FakeResponse:
        assert url == f"{ingest.BASE_URL}/"
        return FakeResponse(json=self.listing)

    def post(self, url: str, json: Any, **_: Any) -> FakeResponse:
        assert json == ingest.CSV_QUERY
        self.posts.append(url.rsplit("/", 1)[1])
        return FakeResponse(content=self.csv)


@pytest.fixture
def lake(tmp_path):
    return LocalFileSystem(auto_mkdir=True), tmp_path.as_posix()


def test_list_tables_keeps_tables_and_compacts_updated():
    assert ingest.list_tables(FakeSession(LISTING)) == [
        ingest.Table("0042M4ARN01", "20261002T081513"),
        ingest.Table("0042M4ARN04", "20261002T081549"),
    ]


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
    assert isinstance(ua, str) and ua.startswith("apip/")
    assert isinstance(ingest.make_session(), requests.Session)
