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


def test_year_extremes_keep_to_one_aisle():
    rows = staples_frame().assign(
        category=["Rice", "Vegetables", "Chicken and eggs"] + ["Rice"] * 4
    )
    fell, rose = data.year_extremes(rows, SEP, 4, aisle="Meat & fish")
    assert fell.empty and list(rose["staple"]) == ["Egg"]


def test_aisles_cover_every_basket_category():
    categories = set(pd.read_csv(data.BASKET)["category"])
    grouped = [c for aisle in data.AISLES.values() for c in aisle]
    assert sorted(grouped) == sorted(categories)


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


def test_peso_buys_compares_kg_now_and_a_year_ago():
    rows = pd.DataFrame(
        {
            "month": [SEP, SEP],
            "geo_code": ["000000000", "130000000"],
            "staple": ["Regular rice", "Regular rice"],
            "price": [50.0, 60.0],
            "price_year_ago": [40.0, None],
        }
    )
    buys = data.peso_buys(rows, SEP)
    assert buys is not None
    assert (buys["kg"], buys["kg_year_ago"]) == (2.0, 2.5)
    assert data.peso_buys(rows, SEP, "130000000") is None  # no year-ago price


def test_swaps_pair_risers_with_distinct_fallers_in_their_group():
    rows = pd.DataFrame(
        {
            "month": [SEP] * 6,
            "geo_code": ["000000000"] * 6,
            "staple": ["Repolyo", "Sayote", "Carrot", "Kalabasa", "Tomato", "Rice"],
            "category": ["Vegetables"] * 5 + ["Rice"],
            "change_year": [0.35, 0.30, -0.28, -0.17, -0.01, 0.25],
        }
    )
    pairs = data.swaps(rows, SEP)
    # Tomato fell under 5%, so it is no swap; rice is not a swap group.
    assert list(zip(pairs["staple"], pairs["swap"], strict=True)) == [
        ("Repolyo", "Carrot"),
        ("Sayote", "Kalabasa"),
    ]


def test_seasonal_flags_keep_only_big_usual_gaps():
    seasons = pd.DataFrame(
        {
            "staple": ["Carrot", "Rice", "Carrot"],
            "calendar_month": [10, 10, 11],
            "seasonal_index": [0.115, -0.001, -0.2],
        }
    )
    assert data.seasonal_flags(seasons, 10) == {"Carrot": 0.115}


def test_movers_ranks_by_size_either_way():
    rows = data.movers(staples_frame(), SEP, "change_month", 2)
    assert list(rows["staple"]) == ["Carrot", "Egg"]


def test_area_values_lists_one_level_cheapest_first():
    rows = data.area_values(staples_frame(), SEP, "province", "staple", "Rice")
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
    provinces = data.area_values(df, SEP, "province", "staple", "Rice")
    regions = data.area_values(df, SEP, "region", "staple", "Rice")
    ncr = regions[regions["geo_code"] == data.NCR]
    props = [
        f["properties"]
        for f in data.map_features(geojson(), provinces, "province", ncr)["features"]
    ]
    assert [p["value"] for p in props] == [40.0, None, 55.0]
    assert props[2]["label"] == "NCR (region figure)"


def test_map_features_at_region_level_colour_provinces_by_region():
    regions = data.area_values(staples_frame(), SEP, "region", "staple", "Rice")
    props = [
        f["properties"]
        for f in data.map_features(geojson(), regions, "region", regions)["features"]
    ]
    assert [p["value"] for p in props] == [45.0, 45.0, 55.0]
    assert [p["label"] for p in props] == ["CAR", "CAR", "NCR"]


def test_dish_breakdown_prices_each_recipe_line():
    recipes = pd.DataFrame(
        {"dish": ["Torta", "Torta"], "staple": ["Egg", "Rice"], "quantity": [6, 0.75]}
    )
    lines = data.dish_breakdown(staples_frame(), recipes, SEP, "000000000", "Torta")
    assert list(lines["staple"]) == ["Egg", "Rice"]
    assert list(lines["line_cost"]) == [54.0, 37.5]


def test_season_extremes_put_the_cheapest_month_first():
    seasons = pd.DataFrame(
        {
            "staple": ["Tomato", "Onion", "Tomato"],
            "calendar_month": [11, 11, 4],
            "seasonal_index": [0.15, -0.05, -0.2],
        }
    )
    assert list(data.season_extremes(seasons, 11)["staple"]) == ["Onion", "Tomato"]


def test_change_words():
    assert data.change_words(0.245) == "24.5% more"
    assert data.change_words(-0.031) == "3.1% less"
    assert data.change_words(0.0004) == "the same"


def test_arrow_pairs_direction_with_a_symbol():
    assert data.arrow(0.041) == "↑ 4.1%"
    assert data.arrow(-0.2) == "↓ 20.0%"
    assert data.arrow(0.0004) == "– 0.0%"


def gap_rows() -> pd.DataFrame:
    """Two regions and a province with three foods' gaps from national."""
    month = pd.Timestamp("2026-10-01")
    rows = [
        # geo_code, geolocation, geo_level, region_code, staple, vs_national
        (
            "130000000",
            "NCR - National Capital Region",
            "region",
            "130000000",
            "Rice",
            0.10,
        ),
        (
            "130000000",
            "NCR - National Capital Region",
            "region",
            "130000000",
            "Egg",
            0.02,
        ),
        (
            "130000000",
            "NCR - National Capital Region",
            "region",
            "130000000",
            "Garlic",
            -0.05,
        ),
        ("070000000", "VII - Central Visayas", "region", "070000000", "Rice", -0.20),
        ("070000000", "VII - Central Visayas", "region", "070000000", "Egg", -0.01),
        ("070000000", "VII - Central Visayas", "region", "070000000", "Garlic", 0.30),
        ("072200000", "Cebu", "province", "070000000", "Rice", -0.30),
        ("072200000", "Cebu", "province", "070000000", "Egg", None),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "geo_code",
            "geolocation",
            "geo_level",
            "region_code",
            "staple",
            "vs_national",
        ],
    )
    return frame.assign(month=month)


def test_typical_gaps_take_the_median_and_rank_the_cheapest_first():
    gaps = data.typical_gaps(gap_rows(), pd.Timestamp("2026-10-01"), "region")
    # Central Visayas: median of -20%, -1%, +30% is -1%; NCR: of +10%, +2%, -5% is +2%.
    assert list(gaps["geolocation"]) == [
        "VII - Central Visayas",
        "NCR - National Capital Region",
    ]
    assert gaps["vs_national"].round(4).tolist() == [-0.01, 0.02]
    assert gaps["rank"].tolist() == [1, 2]
    assert gaps["foods"].tolist() == [3, 3]


def test_gap_history_counts_dearer_foods_and_skips_unpriced_ones():
    history = data.gap_history(gap_rows(), "072200000")
    assert history[["typical", "dearer", "foods"]].values.tolist() == [[-0.30, 0, 1]]


def test_place_names_mark_regions_and_sort_a_to_z():
    names = data.place_names(gap_rows())
    assert list(names.values()) == [
        "Cebu",
        "Central Visayas (region)",
        "National Capital Region (region)",
    ]


def test_region_of_maps_a_province_to_its_region():
    staples = gap_rows()
    assert data.region_of(staples, "072200000") == "070000000"
    assert data.region_of(staples, "130000000") == "130000000"
    assert data.region_of(staples, "000000000") == "000000000"


def test_place_headline_names_the_cheapest_and_priciest_food_here():
    basket = pd.DataFrame(
        {"staple": ["Tilapia", "Rice", "Garlic"], "vs_national": [-0.251, 0.01, 0.302]}
    )
    assert (
        data.place_headline(basket, "Cebu")
        == "In Cebu, tilapia costs 25.1% less than the national average, garlic 30.2% more"
    )


def test_place_headline_leaves_out_a_side_with_no_food():
    pricier = pd.DataFrame({"staple": ["Rice", "Garlic"], "vs_national": [0.01, 0.302]})
    assert data.place_headline(pricier, "Batanes") == (
        "In Batanes, garlic costs 30.2% more than the national average"
    )
    flat = pd.DataFrame({"staple": ["Rice"], "vs_national": [0.0]})
    assert (
        data.place_headline(flat, "Cebu")
        == "In Cebu, food costs the same as the national average"
    )


def moves_rows() -> pd.DataFrame:
    """Cebu, 12 months: talong usually 30% above national, now 5% below (buy);
    sitaw usually 10% below, now 40% above (wait); rice steady at +2% (usual);
    ginger has only 3 months of history, too few to have a usual."""
    months = pd.date_range("2025-10-01", "2026-10-01", freq="MS")
    rows = []
    for i, m in enumerate(months):
        last = i == len(months) - 1
        rows += [
            ("Talong", -0.05 if last else 0.30),
            ("Sitaw", 0.40 if last else -0.10),
            ("Rice", 0.02),
        ]
        rows[-3:] = [(s, g, m) for s, g in rows[-3:]]
        if i >= len(months) - 3:
            rows.append(("Ginger", 0.5, m))
    frame = pd.DataFrame(rows, columns=["staple", "vs_national", "month"])
    return frame.assign(geo_code="072200000", price=100.0, unit="kg")


def test_place_moves_compare_each_gap_with_its_usual_here():
    moves = data.place_moves(moves_rows(), pd.Timestamp("2026-10-01"), "072200000")
    assert moves["staple"].tolist() == ["Talong", "Rice", "Sitaw"]
    assert moves["usual"].round(2).tolist() == [0.30, 0.02, -0.10]
    assert moves["shift"].round(2).tolist() == [-0.35, 0.0, 0.50]
    assert moves["action"].tolist() == ["buy", "usual", "wait"]


def test_rank_words_count_from_the_nearer_end():
    assert data.rank_words(2, 18, "regions") == "2nd cheapest of 18 regions"
    assert data.rank_words(17, 18, "regions") == "2nd most expensive of 18 regions"
    assert (
        data.rank_words(59, 100, "provinces") == "42nd most expensive of 100 provinces"
    )
