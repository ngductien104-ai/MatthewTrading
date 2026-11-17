"""Country outlines for the Atlas map, reduced from Natural Earth 110m (public domain).

Rebuild the compact file after downloading the raw GeoJSON:
    python -m src.atlas.world <path/to/ne_110m_admin_0_countries.geojson>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORLD_FILE = Path(__file__).resolve().parents[2] / "data" / "atlas" / "world_110m.json"


def prepare(raw_path: Path, out_path: Path = WORLD_FILE) -> int:
    """Keep ISO code, name, label point and outer rings (2 decimals) per country."""
    features = json.loads(Path(raw_path).read_text(encoding="utf-8"))["features"]
    world = {}
    for feature in features:
        props, geom = feature["properties"], feature["geometry"]
        iso = props.get("ISO_A2_EH")
        if not iso or iso == "-99":
            iso = props["ADM0_A3"]
        polygons = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        rings = [[[round(x, 2), round(y, 2)] for x, y in polygon[0]] for polygon in polygons]
        world[iso] = {
            "name": props["NAME"],
            "label": [round(props["LABEL_X"], 2), round(props["LABEL_Y"], 2)],
            "rings": rings,
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(world, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(world)


def load(path: Path = WORLD_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(prepare(Path(sys.argv[1])), "countries ->", WORLD_FILE)
