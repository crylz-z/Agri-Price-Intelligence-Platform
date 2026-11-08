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


def shares_frame() -> pd.DataFrame:
    # National Sep 2026 tomato and regular rice (handoff spot values), carrot's
    # latest month is June, and a stale tomato row that is not the latest.
    return pd.DataFrame(
        {
            "month": pd.to_datetime(
                ["2026-09-01", "2026-09-01", "2026-06-01", "2026-08-01", "2026-09-01"]
            ),
            "geo_code": ["000000000"] * 4 + ["030000000"],
            "staple": ["Tomato", "Regular rice", "Carrot", "Tomato", "Tomato"],
            "farmgate_equivalent": [39.02, 20.84 / 0.63, 34.77, 30.0, 50.0],
            "retail_price": [107.82, 50.10, 148.42, 100.0, 40.0],
            "is_latest": [True, True, True, False, True],
        }
    ).assign(farmer_share=lambda d: d["farmgate_equivalent"] / d["retail_price"])


def test_farmer_shares_rank_each_staples_latest_month_smallest_first():
    rows = data.farmer_shares(shares_frame())
    assert list(rows["staple"]) == ["Carrot", "Tomato", "Regular rice"]
    assert rows["month"].dt.strftime("%b %Y").tolist() == [
        "Jun 2026",
        "Sep 2026",
        "Sep 2026",
    ]
    # 34.77 / 148.42 = 0.2343; 39.02 / 107.82 = 0.3619; 33.0794 / 50.10 = 0.6603
    assert rows["farmer"].round(2).tolist() == [23.43, 36.19, 66.03]
    assert rows["rest"].round(2).tolist() == [76.57, 63.81, 33.97]


def test_farmer_shares_clip_the_rest_when_farmgate_tops_retail():
    rows = data.farmer_shares(shares_frame(), "030000000")
    # 50 / 40 = 1.25: ₱125 of every ₱100, nothing left over.
    assert rows["farmer"].tolist() == [125.0]
    assert rows["rest"].tolist() == [0.0]


def test_share_headline_names_the_smallest_share():
    assert data.share_headline(data.farmer_shares(shares_frame())) == (
        "Carrot farmers get ₱23 of every ₱100"
    )


def test_share_history_pairs_retail_and_farmgate_by_month():
    history = data.share_history(shares_frame(), "Tomato")
    assert history.to_dict("records") == [
        {"month": pd.Timestamp("2026-08-01"), "price": 30.0, "line": "Farm"},
        {"month": pd.Timestamp("2026-09-01"), "price": 39.02, "line": "Farm"},
        {"month": pd.Timestamp("2026-08-01"), "price": 100.0, "line": "Store"},
        {"month": pd.Timestamp("2026-09-01"), "price": 107.82, "line": "Store"},
    ]


def test_events_for_match_the_staple_or_its_category():
    events = pd.DataFrame(
        {
            "start_date": pd.to_datetime(["2025-02-03", "2024-07-06", "2024-01-19"]),
            "staple": ["Rice", "Rice", "Red onion"],
            "event": ["emergency", "tariff cut", "onion ban"],
        }
    )
    rice = data.events_for(events, "Regular rice", "Rice")
    assert rice["event"].tolist() == ["tariff cut", "emergency"]
    assert data.events_for(events, "Red onion", "Spices")["event"].tolist() == [
        "onion ban"
    ]
    assert data.events_for(events, "Carrot", "Vegetables").empty


def test_policy_events_seed_loads_with_dates():
    events = data.load_events()
    assert events["start_date"].notna().all()
    assert {"start_date", "end_date", "staple", "event", "source_url"} <= set(events)


def test_dish_wage_shares_rank_one_region_or_the_median_region():
    month = pd.Timestamp("2026-10-01")
    dishes = pd.DataFrame(
        {
            "month": [month] * 5,
            "geo_code": [
                "030000000",
                "030000000",
                "010000000",
                "190000000",
                "000000000",
            ],
            "geolocation": [
                "III - Central Luzon",
                "III - Central Luzon",
                "I - Ilocos Region",
                "Negros Island Region (NIR)",
                "Philippines",
            ],
            "geo_level": ["region", "region", "region", "region", "national"],
            "dish": ["Pinakbet", "Pork adobo", "Pinakbet", "Pinakbet", "Pinakbet"],
            # 249.74 / 600 = 0.4162; 432.60 / 600 = 0.7210; 225.0 / 500 = 0.45
            "dish_wage_share": [249.74 / 600, 432.60 / 600, 225.0 / 500, None, None],
        }
    )
    central = data.dish_wage_shares(dishes, month, "030000000")
    assert central["dish"].tolist() == ["Pork adobo", "Pinakbet"]
    assert central["dish_wage_share"].round(4).tolist() == [0.721, 0.4162]
    # Nationally: Pinakbet's median of 0.4162 and 0.45 (NIR has no wage) = 0.4331.
    country = data.dish_wage_shares(dishes, month)
    assert country["dish"].tolist() == ["Pork adobo", "Pinakbet"]
    assert country["dish_wage_share"].round(4).tolist() == [0.721, 0.4331]
    assert data.dish_wage_shares(dishes, month, "190000000").empty


def test_farmer_cut_compares_like_for_like_a_year_earlier():
    year_ago = pd.DataFrame(
        {
            "month": pd.to_datetime(["2025-09-01", "2025-06-01"]),
            "geo_code": ["000000000"] * 2,
            "staple": ["Tomato", "Carrot"],
            "farmer_share": [0.30, 0.25],
        }
    )
    shares = pd.concat([shares_frame(), year_ago], ignore_index=True)
    rows = data.farmer_shares(shares_frame())
    typical, change = data.farmer_cut(shares, rows)
    # Median of 23.43, 36.19, 66.03 is 36.19. Rice has no year-ago price, so the
    # change uses carrot and tomato only: (23.4268 + 36.1899) / 2 = 29.8083,
    # against (25 + 30) / 2 = 27.5.
    assert round(typical, 2) == 36.19
    assert round(change, 2) == 2.31
    tomato = data.farmer_cut(shares, rows, "Tomato")
    assert (round(tomato[0], 2), round(tomato[1], 2)) == (36.19, 6.19)
    assert data.farmer_cut(shares, rows, "Regular rice")[1] is None
    assert data.farmer_cut(shares, rows, "Garlic") == (None, None)


def test_dinner_cut_takes_the_median_dish_and_its_matched_change():
    now, before = pd.Timestamp("2026-10-01"), pd.Timestamp("2025-10-01")
    dishes = pd.DataFrame(
        {
            "month": [now] * 3 + [before] * 2,
            "geo_code": ["030000000"] * 5,
            "geolocation": ["III - Central Luzon"] * 5,
            "geo_level": ["region"] * 5,
            "dish": ["Adobo", "Pinakbet", "Nilaga", "Adobo", "Pinakbet"],
            "dish_wage_share": [0.60, 0.40, 0.90, 0.50, 0.38],
        }
    )
    typical, change = data.dinner_cut(dishes, now, "030000000")
    # Median of 0.6, 0.4, 0.9 is 0.6; matched: (0.6 + 0.4) / 2 - (0.5 + 0.38) / 2.
    assert typical == 0.6
    assert round(change, 4) == 0.06
    assert data.dinner_cut(dishes, now, "190000000") == (None, None)
