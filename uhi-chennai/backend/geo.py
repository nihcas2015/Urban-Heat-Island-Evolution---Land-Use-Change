"""
backend/geo.py
--------------
GeoJSON builder:
- Chennai: loads from local actual 200-ward GeoJSON file
- Other cities: fetches district GeoJSON from GitHub raw (datta07/INDIAN-SHAPEFILES),
  filters to city's key districts, caches in memory & local filesystem for ultra-fast response.
"""

import json
import os
import urllib.request
import time
from backend.cities import CITIES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Memory cache: city_key -> GeoJSON FeatureCollection
_geom_cache = {}


def _district_name(feature):
    """Extract district name from various GeoJSON property conventions."""
    p = feature.get("properties", {})
    for key in ("dtname", "DISTRICT", "District", "district", "NAME_2", "Dist_Name"):
        val = p.get(key)
        if val:
            return str(val).strip()
    return str(feature.get("id", ""))


def get_city_geojson(city_key):
    """Return filtered district/ward GeoJSON for a city (cached in memory and disk)."""
    if city_key in _geom_cache:
        return _geom_cache[city_key]

    cfg = CITIES.get(city_key, {})

    if cfg.get("use_local_wards"):
        # Chennai: 200 actual municipal ward polygons
        file_path = os.path.join(DATA_DIR, "wards_2024.geojson")
        with open(file_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
        _geom_cache[city_key] = gj
        return gj

    # Check local disk cache first (instant loading)
    cache_path = os.path.join(CACHE_DIR, f"{city_key}_districts.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                gj = json.load(f)
            _geom_cache[city_key] = gj
            return gj
        except Exception:
            pass

    # Remote fetch from GitHub raw
    url = cfg.get("geojson_url")
    if not url:
        return {"type": "FeatureCollection", "features": []}

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UHI-Platform/2.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw_gj = json.loads(r.read().decode("utf-8"))

        district_filter = cfg.get("district_filter")
        if district_filter:
            keep = {d.lower() for d in district_filter}
            features = [
                f for f in raw_gj.get("features", [])
                if _district_name(f).lower() in keep
            ]
        else:
            features = raw_gj.get("features", [])

        gj = {"type": "FeatureCollection", "features": features}

        # Cache on disk
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(gj, f)

        _geom_cache[city_key] = gj
        return gj
    except Exception as e:
        print(f"Error fetching GeoJSON for {city_key}: {e}")
        return {"type": "FeatureCollection", "features": []}


def get_zone_ids(city_key):
    """Return ordered list of zone IDs / district names for a city."""
    gj = get_city_geojson(city_key)
    cfg = CITIES.get(city_key, {})
    ids = []
    if cfg.get("use_local_wards"):
        for f in gj.get("features", []):
            w = f["properties"].get("ward") or f["properties"].get("Ward_No", "")
            if w:
                ids.append(str(w))
    else:
        for f in gj.get("features", []):
            dname = _district_name(f)
            if dname:
                ids.append(dname)
    return ids


def build_indicator_geojson(city_key, rows, indicator="lst"):
    """
    Merge indicator rows into the GeoJSON FeatureCollection.
    rows: list of dicts with keys zone_id, lst, ndvi, ndbi, rainfall, trend, slope, zone_name
    """
    gj = get_city_geojson(city_key)
    cfg = CITIES.get(city_key, {})
    use_wards = cfg.get("use_local_wards", False)

    row_map = {str(r["zone_id"]).lower(): r for r in rows}

    features = []
    for feat in gj.get("features", []):
        if use_wards:
            raw_zid = str(feat["properties"].get("ward") or feat["properties"].get("Ward_No", ""))
        else:
            raw_zid = _district_name(feat)

        row = row_map.get(raw_zid.lower(), {})
        val = row.get(indicator.lower(), 0) or 0

        props = {
            "zone_id": raw_zid,
            "lst": round(row.get("lst", 0) or 0, 4),
            "ndvi": round(row.get("ndvi", 0) or 0, 4),
            "ndbi": round(row.get("ndbi", 0) or 0, 4),
            "rainfall": round(row.get("rainfall", 0) or 0, 2),
            "trend": row.get("trend", "no trend"),
            "slope": round(row.get("slope") or 0, 5),
            "zone_name": row.get("zone_name", raw_zid),
            "indicator_value": round(val, 4),
        }
        features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": features}
