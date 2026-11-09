from pathlib import Path

import pandas as pd

from src.dashboard import data


def test_read_parquet_reads_a_local_lake(tmp_path):
    (tmp_path / "mart").mkdir()
    pd.DataFrame({"staple": ["Tomato"], "farmer_share": [0.36]}).to_parquet(
        tmp_path / data.SHARES
    )
    df = data.read_parquet(tmp_path.as_posix(), data.SHARES)
    assert df.to_dict("records") == [{"staple": "Tomato", "farmer_share": 0.36}]


def shares_frame() -> pd.DataFrame:
    # National Sep 2026 tomato and regular rice (handoff spot values), carrot's
    # latest month is June, and a stale tomato row that is not the latest.
    # Wholesale: tomato 65.33 (Sep 2026), rice 45.0, carrot none; the region's
    # wholesale tops its store price.
    return pd.DataFrame(
        {
            "month": pd.to_datetime(
                ["2026-09-01", "2026-09-01", "2026-06-01", "2026-08-01", "2026-09-01"]
            ),
            "geo_code": ["000000000"] * 4 + ["030000000"],
            "staple": ["Tomato", "Regular rice", "Carrot", "Tomato", "Tomato"],
            "farmgate_equivalent": [39.02, 20.84 / 0.63, 34.77, 30.0, 50.0],
            "retail_price": [107.82, 50.10, 148.42, 100.0, 40.0],
            "wholesale_price": [65.33, 45.0, float("nan"), 60.0, 45.0],
            "is_latest": [True, True, True, False, True],
        }
    ).assign(
        farmer_share=lambda d: d["farmgate_equivalent"] / d["retail_price"],
        trader_cut=lambda d: d["wholesale_price"] - d["farmgate_equivalent"],
    )


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
    # Tomato (65.33 - 39.02) / 107.82 = 24.40; rice (45 - 33.0794) / 50.10 = 23.79.
    assert rows["traders"].round(2).tolist()[1:] == [24.40, 23.79]
    assert rows["stores"].round(2).tolist()[1:] == [39.41, 10.18]
    assert rows[["traders", "stores"]].iloc[0].isna().all()


def test_farmer_shares_clip_the_rest_when_farmgate_tops_retail():
    rows = data.farmer_shares(shares_frame(), "030000000")
    # 50 / 40 = 1.25: ₱125 of every ₱100, nothing left over for anyone.
    assert rows["farmer"].tolist() == [125.0]
    assert rows["rest"].tolist() == [0.0]
    assert rows["traders"].tolist() == [0.0]
    assert rows["stores"].tolist() == [0.0]


# Hand-worked from the farmer's share mart on 2026-11-08 (2018 average vs Oct 2025 -
# Sep 2026 average, national): farm %, store %, middle's cut then and now in pesos,
# middle's cut growth %. Inflation over the same months was +33.4%.
VERDICTS_FIXTURE = (
    Path(__file__).parent / "fixtures" / "marts" / "food_verdicts.parquet"
)
VERDICT_ANSWERS = {
    "Ginger": (42, 103, 31, 89, 191),
    "Sitaw": (76, 96, 24, 53, 121),
    "Red onion": (-17, 48, 62, 125, 102),
    "Potato": (32, 67, 46, 89, 95),
    "Kangkong": (133, 113, 16, 31, 93),
    "Carrot": (38, 64, 55, 99, 81),
    "Repolyo": (-11, 20, 53, 72, 36),
    "Kalabasa": (71, 51, 20, 27, 34),
    "Regular rice": (4, 8, 12, 14, 19),
}


def test_food_verdicts_fixture_matches_the_hand_worked_numbers():
    df = pd.read_parquet(VERDICTS_FIXTURE).set_index("staple")
    for staple, answer in VERDICT_ANSWERS.items():
        row = df.loc[staple]
        got = (
            round(100 * row["farm_change"]),
            round(100 * row["store_change"]),
            round(row["middle_then"]),
            round(row["middle_now"]),
            round(100 * row["middle_change"]),
        )
        assert got == answer, staple
    assert df["cpi_change"].round(3).unique().tolist() == [0.334]


def test_verdicts_clear_only_what_grew_within_5_points_of_inflation():
    df = pd.read_parquet(VERDICTS_FIXTURE)
    cleared = set(df.loc[df["verdict"] == "cleared", "staple"])
    assert cleared == {"Repolyo", "Kalabasa", "Regular rice", "Well-milled rice"}
    # Sayote's +43% sits above the line (33.4 + 5 points), so it stays suspicious.
    assert df.set_index("staple").loc["Sayote", "verdict"] == "suspicious"


def test_national_series_pairs_farm_and_store_by_month():
    shares = pd.DataFrame(
        {
            "staple": ["Red onion"] * 4,
            "geo_code": [data.PHILIPPINES] * 3 + ["130000000"],
            "month": pd.to_datetime(
                ["2023-02-01", "2023-01-01", "2023-03-01", "2023-01-01"]
            ),
            "farmgate_equivalent": [117.0, 216.0, float("nan"), 1.0],
            "wholesale_price": [float("nan"), 400.0, 250.0, 500.0],
            "retail_price": [344.0, 468.0, 300.0, 999.0],
        }
    )
    out = data.national_series(shares, "Red onion")
    # The region and the month with no farm price drop out; months are in order;
    # February has no wholesale price, so only January's is drawn.
    assert out["line"].tolist() == (
        [data.FARM] * 2 + [data.WHOLESALE] + [data.STORE] * 2
    )
    assert out["month"].dt.month.tolist() == [1, 2, 1, 1, 2]
    assert out["price"].tolist() == [216.0, 117.0, 400.0, 468.0, 344.0]


def test_grew_faster_ignores_a_tie_in_whole_percents():
    # Carrot's +80.6% and diesel's +81.1% both show as +81%.
    growth = pd.DataFrame({"middle_change": [1.02, 0.806, 0.5]})
    assert data.grew_faster(growth, 0.811) == 1


def test_growth_vs_prices_ranks_the_biggest_growth_first():
    verdicts = pd.DataFrame(
        {
            "staple": ["A", "B", "C"],
            "middle_change": [0.2, 0.9, 0.5],
            "verdict": ["cleared", "suspicious", "suspicious"],
        }
    )
    out = data.growth_vs_prices(verdicts)
    assert out["staple"].tolist() == ["B", "C", "A"]


def test_claims_for_match_the_staple_or_its_category_newest_first():
    suspects = data.load_suspects()
    rice = data.claims_for(suspects, "Regular rice", "Rice")
    assert len(rice) == 2 and set(rice["staple"]) == {"Rice"}
    onion = data.claims_for(suspects, "Red onion", "Spices")
    assert onion["source_date"].is_monotonic_decreasing
    assert data.claims_for(suspects, "Egg", "Poultry").empty


def test_suspects_seed_has_a_source_for_every_claim():
    suspects = data.load_suspects()
    assert set(suspects["role"]) <= {"suspect", "alibi"}
    assert (
        suspects[["claim", "status", "source_name", "source_url"]].notna().all().all()
    )
    assert suspects["source_url"].str.startswith("https://").all()


def test_up_and_down_scale_to_10_pesos_and_drop_thin_foods():
    verdicts = pd.DataFrame(
        {
            "staple": ["Onion", "Rice", "Egg"],
            "up_months": [18, 17, 5],
            "down_months": [26, 19, 0],
            "up_pass_through": [1.5, 0.9, 0.7],
            "down_pass_through": [0.9, 0.8, None],
        }
    )
    out = data.up_and_down(verdicts)
    assert out["staple"].tolist() == ["Rice", "Onion"]
    assert out["up"].round(1).tolist() == [9.0, 15.0]
    assert out["down"].round(1).tolist() == [8.0, 9.0]


def test_food_verdicts_fixture_moves_up_fast_and_down_slow():
    # Inflation-adjusted, from the local lake on 2026-11-08: the typical food's
    # store price rises ₱9.6 per ₱10 farm rise but falls ₱7.6 per ₱10 farm fall.
    moves = data.up_and_down(pd.read_parquet(VERDICTS_FIXTURE))
    assert len(moves) == 16
    assert round(moves["up"].median(), 1) == 9.6
    assert round(moves["down"].median(), 1) == 7.6
    assert int((moves["down"] < moves["up"]).sum()) == 14


def test_typical_peso_averages_foods_with_all_three_parts_to_100():
    # Tomato 36.19 / 24.40 / 39.41 and rice 66.03 / 23.79 / 10.18; carrot has no
    # wholesale price, so it drops out.
    parts, foods = data.typical_peso(data.farmer_shares(shares_frame()))
    assert foods == 2
    assert {k: round(v, 2) for k, v in parts.items()} == {
        data.FARMER: 51.11,
        data.TRADERS: 24.10,
        data.STORES: 24.79,
    }
    assert round(sum(parts.values()), 6) == 100


def test_whole_centavos_keep_the_total_when_rounding_would_drift():
    assert data.whole_centavos({"a": 33.4, "b": 33.3, "c": 33.3}) == {
        "a": 34,
        "b": 33,
        "c": 33,
    }
    # Plain rounding gives 45 + 23 + 33 = 101.
    assert sum(data.whole_centavos({"a": 44.5, "b": 22.6, "c": 32.9}).values()) == 100


def test_food_verdicts_fixture_typical_peso_is_44_23_33():
    shares = pd.read_parquet(
        Path(__file__).parent / "fixtures/marts/farmer_share_monthly.parquet"
    )
    parts, foods = data.typical_peso(data.farmer_shares(shares))
    assert foods == 17
    assert data.whole_centavos(parts) == {
        data.FARMER: 44,
        data.TRADERS: 23,
        data.STORES: 33,
    }


def test_parts_then_now_are_medians_skipping_foods_without_wholesale():
    verdicts = pd.DataFrame(
        {
            "trader_part_then": [-2.5, 15.0, 20.0, None],
            "trader_part_now": [20.0, 21.0, 22.0, None],
            "store_part_then": [43.0, 34.0, 30.0, None],
            "store_part_now": [38.0, 36.0, 40.0, None],
        }
    )
    assert data.parts_then_now(verdicts) == {
        "trader_part_then": 15.0,
        "trader_part_now": 21.0,
        "store_part_then": 34.0,
        "store_part_now": 38.0,
    }


def test_ratchet_returns_the_farm_to_its_start_and_lifts_the_store():
    # Up ₱9.6 rounds to 10, down ₱7.6 to 8: the store ends 3 x ₱2 = ₱6 higher.
    steps = data.ratchet(9.6, 7.6, swings=3)
    farm = steps[steps["line"] == data.FARM]["price"].tolist()
    store = steps[steps["line"] == data.STORE]["price"].tolist()
    assert farm == [0, 10, 0, 10, 0, 10, 0]
    assert store == [0, 10, 2, 12, 4, 14, 6]


def test_food_verdicts_fixture_traders_part_grew_more_than_stores():
    # From the local lake on 2026-11-09: traders ₱16 -> ₱21, stores ₱34 -> ₱36.
    parts = data.parts_then_now(pd.read_parquet(VERDICTS_FIXTURE))
    assert {k: round(v) for k, v in parts.items()} == {
        "trader_part_then": 16,
        "trader_part_now": 21,
        "store_part_then": 34,
        "store_part_now": 36,
    }


def test_farm_fell_keeps_only_falling_farm_prices_biggest_split_first():
    changes = pd.DataFrame(
        {
            "staple": ["Up", "Both down", "Farm down store up", "Store flat"],
            "farm_change": [0.30, -0.20, -0.10, -0.05],
            "store_change": [0.10, -0.18, 0.10, 0.0],
        }
    )
    rows = data.farm_fell(changes)
    assert list(rows["staple"]) == ["Farm down store up", "Store flat", "Both down"]


def test_price_changes_fixture_tomato_farm_down_26_store_up_13():
    changes = pd.read_parquet(
        Path(__file__).parent / "fixtures" / "marts" / "price_changes_yearly.parquet"
    )
    fell = data.farm_fell(changes)
    top = fell.iloc[0]
    assert top["staple"] == "Tomato"
    assert round(top["farm_change"] * 100) == -26
    assert round(top["store_change"] * 100) == 13
    assert int((fell["store_change"] > 0).sum()) == 4
    pork = changes[changes["staple"] == "Pork kasim"].iloc[0]
    assert pork["farm_measure"] == "live weight"
    assert round(pork["farm_change"] * 100) == -19
