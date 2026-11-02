from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq
import pytest
from fsspec.implementations.local import LocalFileSystem

from src.core.config import REGION_MAP
from src.etl import pipeline

PHT = ZoneInfo("Asia/Manila")
NOW = datetime(2026, 10, 28, 12, 0, 5, tzinfo=PHT)
POSTED = date(2026, 10, 28)


def make_records(now=NOW, posted=POSTED, price=100.0, regions=REGION_MAP, n=3):
    return [
        {
            "extract_dt": now,
            "region_id": rid,
            "region_name": rname,
            "market_name": f"MARKET {m}",
            "commodity_group": "Rice",
            "commodity_name": "Rice - Regular",
            "specifications": "Regular",
            "price": price,
            "raw_date_text": posted.strftime("%B %d, %Y"),
            "posting_date": posted,
        }
        for rid, rname in regions.items()
        for m in range(n)
    ]


@pytest.fixture
def lake(tmp_path):
    return LocalFileSystem(auto_mkdir=True), tmp_path.as_posix()


def read_clean(fs, root, posted=POSTED):
    with fs.open(f"{root}/clean/posting_date={posted}/prices.parquet", "rb") as f:
        return pq.read_table(f)


def test_run_writes_one_raw_object_and_one_clean_partition(lake):
    fs, root = lake
    pipeline.run(fs, root, make_records(), NOW)

    raws = fs.find(f"{root}/raw")
    assert [p.split("/raw/")[1] for p in raws] == [
        "scrape_date=2026-10-28/run=120005.parquet"
    ]
    clean = read_clean(fs, root)
    assert clean.num_rows == len(REGION_MAP) * 3
    assert clean.column("posting_date")[0].as_py() == POSTED


def test_latest_scrape_wins_and_raw_is_kept(lake):
    fs, root = lake
    later = NOW + timedelta(hours=8)
    pipeline.run(fs, root, make_records(price=100.0), NOW)
    pipeline.run(fs, root, make_records(now=later, price=120.0), later)

    assert len(fs.find(f"{root}/raw")) == 2
    clean = read_clean(fs, root)
    assert clean.num_rows == len(REGION_MAP) * 3
    assert set(clean.column("price").to_pylist()) == {120.0}


def test_rerun_gives_identical_clean(lake):
    fs, root = lake
    pipeline.run(fs, root, make_records(), NOW)
    first = read_clean(fs, root)
    pipeline.run(fs, root, make_records(), NOW + timedelta(seconds=1))
    second = read_clean(fs, root)
    assert first.drop(["extract_dt"]).equals(second.drop(["extract_dt"]))


def test_only_touched_posting_dates_are_rebuilt(lake):
    fs, root = lake
    yesterday = POSTED - timedelta(days=1)
    pipeline.run(fs, root, make_records(posted=yesterday), NOW - timedelta(days=1))
    before = fs.info(f"{root}/clean/posting_date={yesterday}/prices.parquet")["mtime"]
    pipeline.run(fs, root, make_records(), NOW)
    after = fs.info(f"{root}/clean/posting_date={yesterday}/prices.parquet")["mtime"]
    assert before == after


def test_failed_checks_write_raw_but_not_clean(lake):
    fs, root = lake
    with pytest.raises(pipeline.ChecksFailed, match="price"):
        pipeline.run(fs, root, make_records(price=0.0), NOW)
    assert len(fs.find(f"{root}/raw")) == 1
    assert not fs.exists(f"{root}/clean")


def test_zero_rows_fails_without_writing(lake):
    fs, root = lake
    with pytest.raises(pipeline.ChecksFailed, match="0 rows"):
        pipeline.run(fs, root, [], NOW)
    assert not fs.exists(f"{root}/raw")


def test_missing_regions_fail(lake):
    fs, root = lake
    few = dict(list(REGION_MAP.items())[:14])
    with pytest.raises(pipeline.ChecksFailed, match="regions"):
        pipeline.run(fs, root, make_records(regions=few), NOW)


def test_future_posting_date_fails(lake):
    fs, root = lake
    posted = POSTED + timedelta(days=1)
    with pytest.raises(pipeline.ChecksFailed, match="posting_date"):
        pipeline.run(fs, root, make_records(posted=posted), NOW)


def test_stale_region_warns_and_publishes(lake):
    fs, root = lake
    stale_id = next(iter(REGION_MAP))
    records = make_records()
    for r in records:
        if r["region_id"] == stale_id:
            r["posting_date"] = POSTED - timedelta(days=51)
    warnings = pipeline.run(fs, root, records, NOW)
    assert any(REGION_MAP[stale_id] in w and "51 days" in w for w in warnings)
    assert read_clean(fs, root).num_rows == (len(REGION_MAP) - 1) * 3


def test_stale_partition_keeps_other_regions_rows(lake):
    fs, root = lake
    old = POSTED - timedelta(days=20)
    then = NOW - timedelta(days=20)
    pipeline.run(fs, root, make_records(now=then, posted=old), then)

    stale_id = next(iter(REGION_MAP))
    records = make_records()
    for r in records:
        if r["region_id"] == stale_id:
            r["posting_date"] = old
    pipeline.run(fs, root, records, NOW)

    assert read_clean(fs, root, old).num_rows == len(REGION_MAP) * 3


def test_row_drop_warns_until_window_is_full_then_fails(lake):
    fs, root = lake
    for d in range(14, 0, -1):
        then = NOW - timedelta(days=d)
        pipeline.run(fs, root, make_records(now=then, posted=then.date(), n=10), then)
    # 14 prior scrape dates: the window is full, so a 70% drop now fails
    with pytest.raises(pipeline.ChecksFailed, match="median"):
        pipeline.run(fs, root, make_records(n=3), NOW)


def test_row_drop_only_warns_on_young_lake(lake):
    fs, root = lake
    then = NOW - timedelta(days=1)
    pipeline.run(fs, root, make_records(now=then, posted=then.date(), n=10), then)
    warnings = pipeline.run(fs, root, make_records(n=3), NOW)
    assert any("median" in w for w in warnings)


def test_price_outlier_only_warns(lake):
    fs, root = lake
    records = make_records(n=20)
    records[0]["price"] = 100_000.0
    warnings = pipeline.run(fs, root, records, NOW)
    assert any("outlier" in w for w in warnings)


def test_duplicate_keys_within_run_only_warn(lake):
    fs, root = lake
    records = make_records()
    records.append({**records[0], "price": 999.0})
    warnings = pipeline.run(fs, root, records, NOW)
    assert any("1 duplicate keys within this run" in w for w in warnings)


def test_checks_catch_duplicate_and_null_keys():
    from src.etl import checks

    table = pipeline.to_table(make_records())
    dupes = pipeline.to_table(make_records() + make_records()[:1])
    errors, _ = checks.check(table, dupes, POSTED, [], window_full=False)
    assert any("duplicate" in e for e in errors)

    nulls = make_records()
    nulls[0]["market_name"] = None
    errors, _ = checks.check(table, pipeline.to_table(nulls), POSTED, [], False)
    assert any("null" in e for e in errors)
