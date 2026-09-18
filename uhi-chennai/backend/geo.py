"""
backend/geo.py
--------------
Builds GeoJSON FeatureCollections from ward geometries + indicator data.
All functions return plain Python dicts (JSON-serialisable).
GeoJSON builder.
- Chennai: loads from local ward-level file
- Other cities: fetches district GeoJSON from GitHub raw on first request,
  filters to configured districts, caches in module-level dict.
  Uses /tmp on Vercel for cross-invocation caching.
GeoJSON builder:
- Chennai: loads from local actual 200-ward GeoJSON file
- Other cities: fetches district GeoJSON from GitHub raw (datta07/INDIAN-SHAPEFILES),
  filters to city's key districts, caches in memory & local filesystem for ultra-fast response.
"""

import json
import os
import json, os, urllib.request, time

import urllib.request
import time
from backend.cities import CITIES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Geometry cache — loaded once
_geom_cache = None
# Memory cache: city_key → GeoJSON FeatureCollection
# Memory cache: city_key -> GeoJSON FeatureCollection
_geom_cache = {}

# Seconds to consider cached data fresh (12 hours)
_CACHE_TTL = 43200
_cache_time = {}

def _load_geometries():
    global _geom_cache
    if _geom_cache is None:
def _district_name(feature):
    """Extract district name from various GeoJSON property conventions."""
    p = feature.get("properties", {})
    for key in ("dtname", "DISTRICT", "District", "district", "NAME_2", "Dist_Name"):
        val = p.get(key)
        if val:
            return str(val).strip()
    return str(feature.get("id", ""))

def _tmp_path(city_key):
    return os.path.join("/tmp", f"uhi_geom_{city_key}.json")


def get_city_geojson(city_key):
    """Return full ward/district GeoJSON for a city (geometry only, no indicator data)."""
    """Return filtered district/ward GeoJSON for a city (cached in memory and disk)."""
    if city_key in _geom_cache:
        return _geom_cache[city_key]

    # Check /tmp cache (Vercel warm-start reuse)
    tmp = _tmp_path(city_key)
    if os.path.exists(tmp) and (time.time() - os.path.getmtime(tmp)) < _CACHE_TTL:
        with open(tmp) as f:
            gj = json.load(f)
        _geom_cache[city_key] = gj
        return gj

    cfg = CITIES.get(city_key, {})

    if cfg.get("use_local_wards"):
        # Chennai — use pre-computed ward-level geojson
        with open(os.path.join(DATA_DIR, "wards_2024.geojson")) as f:
        # Chennai: 200 actual municipal ward polygons
        file_path = os.path.join(DATA_DIR, "wards_2024.geojson")
        with open(file_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
        _geom_cache = {}
        for feat in gj["features"]:
            p = feat["properties"]
            ward_id = int(p.get("ward", p.get("Ward_No", 0)))
            _geom_cache[ward_id] = feat["geometry"]
    return _geom_cache
        # Normalise property key to 'zone_id'
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

def build_ward_geojson(ward_rows, indicator="lst"):
    req = urllib.request.Request(url, headers={"User-Agent": "UHI-Monitor/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        gj = json.loads(r.read().decode())
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UHI-Platform/2.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw_gj = json.loads(r.read().decode("utf-8"))

    # Filter to configured districts
    district_filter = cfg.get("district_filter")
    if district_filter:
        keep = set(d.lower() for d in district_filter)
        gj["features"] = [
            f for f in gj["features"]
            if _district_name(f).lower() in keep
        ]
        district_filter = cfg.get("district_filter")
        if district_filter:
            keep = {d.lower() for d in district_filter}
            features = [
                f for f in raw_gj.get("features", [])
                if _district_name(f).lower() in keep
            ]
        else:
            features = raw_gj.get("features", [])

    # Write to /tmp
    try:
        with open(tmp, "w") as f:
        gj = {"type": "FeatureCollection", "features": features}

        # Cache on disk
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(gj, f)
    except Exception:
        pass

    _geom_cache[city_key] = gj
    return gj
        _geom_cache[city_key] = gj
        return gj
    except Exception as e:
        print(f"Error fetching GeoJSON for {city_key}: {e}")
        return {"type": "FeatureCollection", "features": []}


def _district_name(feature):
    """Extract district name from a variety of property key names."""
    p = feature.get("properties", {})
    for key in ("DISTRICT", "District", "district", "NAME_2", "dtname", "Dist_Name"):
        if key in p and p[key]:
            return str(p[key])
    return ""


def get_zone_ids(city_key):
    """Return list of zone IDs (ward numbers or district names) for a city."""
    """Return ordered list of zone IDs / district names for a city."""
    gj = get_city_geojson(city_key)
    cfg = CITIES.get(city_key, {})
    ids = []
    if cfg.get("use_local_wards"):
        for f in gj["features"]:
        for f in gj.get("features", []):
            w = f["properties"].get("ward") or f["properties"].get("Ward_No", "")
            if w:
                ids.append(str(w))
    else:
        for f in gj["features"]:
            ids.append(_district_name(f) or str(f.get("id", "")))
        for f in gj.get("features", []):
            dname = _district_name(f)
            if dname:
                ids.append(dname)
    return ids


def build_indicator_geojson(city_key, rows, indicator="lst"):
    """
    ward_rows: list of dicts with keys ward, lst, ndvi, ndbi, rainfall,
               trend, zone_name from db.get_wards_summary()
    Returns a GeoJSON FeatureCollection.
    Merge indicator rows into a GeoJSON FeatureCollection.
    rows: list of dicts with keys zone_id, lst, ndvi, ndbi, rainfall, trend, zone_name
    Merge indicator rows into the GeoJSON FeatureCollection.
    rows: list of dicts with keys zone_id, lst, ndvi, ndbi, rainfall, trend, slope, zone_name
    """
    geoms = _load_geometries()
    gj = get_city_geojson(city_key)
    cfg = CITIES.get(city_key, {})
    use_wards = cfg.get("use_local_wards", False)

    # Build lookup: zone_id → row
    row_map = {}
    for r in rows:
        row_map[str(r["zone_id"])] = r
    row_map = {str(r["zone_id"]).lower(): r for r in rows}

    features = []
    for row in ward_rows:
        wid = row["ward"]
        geom = geoms.get(wid)
        if geom is None:
            continue
    for feat in gj["features"]:
    for feat in gj.get("features", []):
        if use_wards:
            zid = str(feat["properties"].get("ward") or feat["properties"].get("Ward_No", ""))
            raw_zid = str(feat["properties"].get("ward") or feat["properties"].get("Ward_No", ""))
        else:
            zid = _district_name(feat)
            raw_zid = _district_name(feat)

        row = row_map.get(zid, {})
        row = row_map.get(raw_zid.lower(), {})
        val = row.get(indicator.lower(), 0) or 0

        props = {
            "zone_id":   zid,
            "lst":       round(row.get("lst", 0) or 0, 4),
            "ndvi":      round(row.get("ndvi", 0) or 0, 4),
            "ndbi":      round(row.get("ndbi", 0) or 0, 4),
            "rainfall":  round(row.get("rainfall", 0) or 0, 2),
            "trend":     row.get("trend", ""),
            "slope":     round(row.get("slope") or 0, 5),
            "zone_name": row.get("zone_name", zid),
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
            "geometry": geom,
            "properties": {
                "ward": wid,
                "lst": round(row["lst"], 4),
                "ndvi": round(row["ndvi"], 4),
                "ndbi": round(row["ndbi"], 4),
                "rainfall": round(row["rainfall"], 2),
                "trend": row.get("trend", ""),
                "slope": round(row.get("slope") or 0, 5),
                "zone_name": row.get("zone_name", ""),
                "zone": row.get("zone", ""),
                "indicator_value": round(row.get(indicator.lower(), 0), 4)
            }
            "geometry": feat["geometry"],
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": features}


def get_zone_list():
    """Unique zone names from geometry metadata."""
    geoms = _load_geometries()
    with open(os.path.join(DATA_DIR, "wards_2024.geojson")) as f:
        gj = json.load(f)
    zones = set()
    for feat in gj["features"]:
        z = feat["properties"].get("Zone name", "")
        if z:
            zones.add(z)
    return sorted(zones)

