import duckdb
import pandas as pd
import pytest

from src.dashboard import data

ROWS = """
    SELECT * REPLACE (price::DOUBLE AS price) FROM (VALUES
        (DATE '2026-08-01', '000000000', 'Philippines', 'national', 'Cereals', 'RICE', 55.0),
        (DATE '2026-09-01', '000000000', 'Philippines', 'national', 'Cereals', 'RICE', 55.68),
        (DATE '2026-09-01', '130000000', 'NCR - National Capital Region', 'region', 'Cereals', 'RICE', 60.0),
        (DATE '2026-09-01', '140000000', 'CAR - Cordillera Administrative Region', 'region', 'Cereals', 'RICE', 52.0),
        (DATE '2026-09-01', '140100000', 'Abra', 'province', 'Cereals', 'RICE', 50.0)
    ) AS t(month, geo_code, geolocation, geo_level, commodity_group, commodity, price)
"""


def make_lake(tmp_path) -> str:
    root = tmp_path.as_posix()
    (tmp_path / "mart").mkdir()
    duckdb.sql(f"COPY ({ROWS}) TO '{root}/{data.MART}' (FORMAT parquet)")
    return root


def test_read_mart_reads_the_parquet(tmp_path):
    df = data.read_mart(make_lake(tmp_path))
    assert len(df) == 5
    assert set(df["geo_level"]) == {"national", "region", "province"}


def test_places_put_national_then_regions_then_provinces(tmp_path):
    df = data.read_mart(make_lake(tmp_path))
    assert list(data.places(df).values()) == [
        "Philippines",
        "CAR - Cordillera Administrative Region",
        "NCR - National Capital Region",
        "Abra",
    ]


def test_item_names_put_basket_foods_first_under_their_plain_names():
    retail = pd.DataFrame({"commodity": ["SQUASH, 1 KG", "RICE, 1 KG", "OKRA, 1 KG"]})
    basket = pd.DataFrame(
        {"commodity": ["SQUASH, 1 KG", "RICE, 1 KG"], "staple": ["Kalabasa", "Rice"]}
    )
    assert data.item_names(retail, basket) == {
        "SQUASH, 1 KG": "Kalabasa",
        "RICE, 1 KG": "Rice",
        "OKRA, 1 KG": "Okra, 1 Kg",
    }


def test_lookup_matches_year_ago_and_national_by_month():
    # Abra skips August 2025, so row order would pick the wrong year-ago price.
    retail = pd.DataFrame(
        {
            "month": pd.to_datetime(
                ["2025-07-01", "2025-09-01", "2026-09-01", "2026-09-01"]
            ),
            "geo_code": ["140100000", "140100000", "140100000", "000000000"],
            "geo_level": ["province", "province", "province", "national"],
            "commodity": ["RICE"] * 4,
            "price": [30.0, 40.0, 50.0, 40.0],
        }
    )
    found = data.lookup(retail, "RICE", "140100000")
    assert found["month"] == pd.Timestamp("2026-09-01")
    assert found["price"] == 50.0
    assert found["change_year"] == pytest.approx(0.25)
    assert found["vs_national"] == pytest.approx(0.25)
    assert "price" not in data.lookup(retail, "RICE", "999")


SEP = pd.Timestamp("2026-09-01")


def staples_frame() -> pd.DataFrame:
    rows = [
        # month, geo_code, geolocation, geo_level, staple, unit, price, m/m, y/y, vs nat
        (
            SEP,
            "000000000",
            "Philippines",
            "national",
            "Rice",
            "kg",
            50.0,
            0.01,
            0.25,
            0.0,
        ),
        (
            SEP,
            "000000000",
            "Philippines",
            "national",
            "Carrot",
            "kg",
            132.0,
            0.04,
            -0.27,
            0.0,
        ),
        (
            SEP,
            "000000000",
            "Philippines",
            "national",
            "Egg",
            "pc",
            9.0,
            -0.30,
            0.05,
            0.0,
        ),
        (SEP, "130000000", "NCR", "region", "Rice", "kg", 55.0, 0.0, 0.2, 0.1),
        (SEP, "140000000", "CAR", "region", "Rice", "kg", 45.0, 0.0, 0.2, -0.1),
        (SEP, "140100000", "Abra", "province", "Rice", "kg", 40.0, 0.0, 0.2, -0.2),
        (SEP, "141100000", "Benguet", "province", "Rice", "kg", 60.0, 0.0, 0.2, 0.2),
    ]
    cols = ["month", "geo_code", "geolocation", "geo_level", "staple", "unit",
            "price", "change_month", "change_year", "vs_national"]  # fmt: skip
    return pd.DataFrame(rows, columns=cols)


def test_basket_summary_counts_moves_and_names_the_extremes():
    summary = data.basket_summary(staples_frame(), SEP)
    assert (summary["staples"], summary["dearer"], summary["cheaper"]) == (3, 2, 1)
    assert summary["top"]["staple"] == "Rice"
    assert summary["bottom"]["staple"] == "Carrot"
    assert summary["median"] == 0.05


def test_year_extremes_splits_falls_and_rises_biggest_first():
    fell, rose = data.year_extremes(staples_frame(), SEP, 4)
    assert list(fell["staple"]) == ["Carrot"]
    assert list(rose["staple"])[0] == "Rice"
    assert (rose["change_year"] > 0).all()


def test_headline_names_biggest_rise_and_fall():
    rose = pd.DataFrame({"staple": ["Repolyo"], "change_year": [0.349]})
    fell = pd.DataFrame({"staple": ["Carrot"], "change_year": [-0.285]})
    none = rose.iloc[0:0]
    assert data.headline(rose, fell) == "Repolyo up 34.9%, carrot down 28.5%"
    assert data.headline(none, fell) == "Carrot down 28.5%"
    assert data.headline(none, none) == "Prices held steady"


def test_regions_put_the_country_first_then_short_names_a_to_z():
    names = data.regions(staples_frame())
    assert names == {"000000000": "Philippines", "140000000": "CAR", "130000000": "NCR"}
    psa = pd.DataFrame(
        {
            "geo_code": ["1"],
            "geolocation": ["IV-A - CALABARZON"],
            "geo_level": ["region"],
        }
    )
    assert data.regions(psa)["1"] == "CALABARZON"


def test_in_words_adds_the_where_english_needs_it():
    assert data.in_words("000000000", "Philippines") == "the Philippines"
    assert (
        data.in_words("1", "National Capital Region") == "the National Capital Region"
    )
    assert data.in_words("9", "Zamboanga Peninsula") == "the Zamboanga Peninsula"
    assert data.in_words("3", "Central Luzon") == "Central Luzon"


def test_helpers_read_one_place():
    fell, rose = data.year_extremes(staples_frame(), SEP, 4, "130000000")
    assert fell.empty and list(rose["staple"]) == ["Rice"]
    assert data.basket_summary(staples_frame(), SEP, "130000000")["staples"] == 1


def test_area_values_lists_one_level_cheapest_first():
    rows = data.area_values(staples_frame(), SEP, "province", "Rice")
    assert list(rows["geolocation"]) == ["Abra", "Benguet"]
    assert list(rows["value"]) == [40.0, 60.0]


def geojson() -> dict:
    def feature(name, geo_code, region_code):
        props = {"name": name, "geo_code": geo_code, "region_code": region_code}
        return {"type": "Feature", "properties": props, "geometry": None}

    return {
        "features": [
            feature("Abra", "140100000", "140000000"),
            feature("Kalinga", "143200000", "140000000"),
            feature("NCR, Second District", None, "130000000"),
        ]
    }


def test_map_features_at_province_level_fill_ncr_from_its_region():
    df = staples_frame()
    provinces = data.area_values(df, SEP, "province", "Rice")
    regions = data.area_values(df, SEP, "region", "Rice")
    ncr = regions[regions["geo_code"] == data.NCR]
    props = [
        f["properties"]
        for f in data.map_features(geojson(), provinces, "province", ncr)["features"]
    ]
    assert [p["value"] for p in props] == [40.0, None, 55.0]
    assert props[2]["label"] == "NCR (region figure)"


def test_map_features_at_region_level_colour_provinces_by_region():
    regions = data.area_values(staples_frame(), SEP, "region", "Rice")
    props = [
        f["properties"]
        for f in data.map_features(geojson(), regions, "region", regions)["features"]
    ]
    assert [p["value"] for p in props] == [45.0, 45.0, 55.0]
    assert [p["label"] for p in props] == ["CAR", "CAR", "NCR"]


def test_arrow_pairs_direction_with_a_symbol():
    assert data.arrow(0.041) == "↑ 4.1%"
    assert data.arrow(-0.2) == "↓ 20.0%"
    assert data.arrow(0.0004) == "– 0.0%"


def test_typical_change_history_takes_each_months_median():
    rows = staples_frame()
    earlier = rows.assign(month=pd.Timestamp("2026-08-01"), change_year=0.1)
    history = data.typical_change_history(pd.concat([rows, earlier]))
    assert history["month"].tolist() == [pd.Timestamp("2026-08-01"), SEP]
    # September national: median of +25%, -27%, +5% is +5%.
    assert history["typical"].round(4).tolist() == [0.1, 0.05]


def test_region_prices_list_the_latest_month_cheapest_first():
    retail = pd.DataFrame(
        {
            "month": pd.to_datetime(["2026-09-01"] * 3 + ["2026-08-01"]),
            "geo_code": ["000000000", "130000000", "140000000", "140000000"],
            "geolocation": ["Philippines", "NCR - National Capital Region",
                            "CAR - Cordillera Administrative Region", "CAR - x"],
            "geo_level": ["national", "region", "region", "region"],
            "commodity": ["RICE"] * 4,
            "price": [50.0, 60.0, 45.0, 10.0],
        }
    )  # fmt: skip
    rows = data.region_prices(retail, "RICE")
    assert rows["region"].tolist() == [
        "Cordillera Administrative Region",
        "National Capital Region",
    ]
    assert rows["price"].tolist() == [45.0, 60.0]
