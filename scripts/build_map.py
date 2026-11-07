"""Build the dashboard's province map from faeldon/philippines-json-maps (MIT).

Download the low-resolution province files (PSGC 2026-3Q) into one folder, then:

    uv run python scripts/build_map.py <folder>

Each feature gets the PSA `geo_code` it is priced under and PSA's `region_code`, so
the dashboard joins the map to the marts without matching names at runtime.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

SEED = Path("dbt/seeds/geolocations.csv")
OUT = Path("src/dashboard/assets/ph_provinces.geojson")
NCR, BARMM = "130000000", "150000000"
# Map names that differ from PSA's labels. NCR has no provinces in PSA's data and the
# Special Geographic Area has no prices, so they carry only a region.
RENAMES = {
    "Cotabato": "Cotabato (North Cotabato)",
    "Davao de Oro": "Davao de Oro (Compostela Valley)",
    "Maguindanao del Norte": "Maguindanao",
    "Maguindanao del Sur": "Maguindanao",
    "City of Isabela (Not a Province)": "City of Isabela",
}


def rounded(coords: object) -> object:
    if isinstance(coords, list):
        return [rounded(c) for c in coords]
    return round(float(coords), 3)  # type: ignore[arg-type]


def d3_winding(polygon: list[list[list[float]]]) -> list[list[list[float]]]:
    """Vega draws with d3, which wants outer rings clockwise and holes
    counter-clockwise: the reverse of the source's RFC 7946 order. A ring the wrong
    way round fills the whole globe instead of the province."""

    def area(ring: list[list[float]]) -> float:
        return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))

    return [
        ring if (area(ring) < 0) == (i == 0) else ring[::-1]
        for i, ring in enumerate(polygon)
    ]


def geometry(geom: dict[str, Any]) -> dict[str, Any]:
    coords: Any = rounded(geom["coordinates"])
    if geom["type"] == "Polygon":
        coords = d3_winding(coords)
    else:
        coords = [d3_winding(polygon) for polygon in coords]
    return {"type": geom["type"], "coordinates": coords}


def main(folder: Path) -> None:
    seed = list(csv.DictReader(SEED.open(newline="")))
    by_name = {r["geolocation"]: r for r in seed if r["geo_level"] == "province"}
    features = []
    for path in sorted(folder.glob("provdists-region-*.json")):
        for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
            name = feature["properties"]["adm2_en"]
            if name.startswith("NCR"):
                geo_code, region_code = None, NCR
            elif name == "Special Geographic Area":
                geo_code, region_code = None, BARMM
            else:
                row = by_name[RENAMES.get(name, name)]
                geo_code, region_code = row["geo_code"], row["region_code"]
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "name": name,
                        "geo_code": geo_code,
                        "region_code": region_code,
                    },
                    "geometry": geometry(feature["geometry"]),
                }
            )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features}, separators=(",", ":")
        ),
        encoding="utf-8",
    )
    print(f"{len(features)} features -> {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
