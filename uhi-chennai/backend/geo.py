"""
backend/geo.py
--------------
GeoJSON builder.
- Chennai: loads from local ward-level file
- Other cities: fetches district GeoJSON from GitHub raw on first request,
  filters to configured districts, caches in module-level dict.
  Uses /tmp on Vercel for cross-invocation caching.
"""

import json, os, urllib.request, time

from backend.cities import CITIES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Memory cache: city_key → GeoJSON FeatureCollection
_geom_cache = {}

# Seconds to consider cached data fresh (12 hours)
_CACHE_TTL = 43200
_cache_time = {}


def _tmp_path(city_key):
    return os.path.join("/tmp", f"uhi_geom_{city_key}.json")


def get_city_geojson(city_key):
    """Return full ward/district GeoJSON for a city (geometry only, no indicator data)."""
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
            gj = json.load(f)
        # Normalise property key to 'zone_id'
        _geom_cache[city_key] = gj
        return gj

    # Remote fetch from GitHub raw
    url = cfg.get("geojson_url")
    if not url:
        return {"type": "FeatureCollection", "features": []}

    req = urllib.request.Request(url, headers={"User-Agent": "UHI-Monitor/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        gj = json.loads(r.read().decode())

    # Filter to configured districts
    district_filter = cfg.get("district_filter")
    if district_filter:
        keep = set(d.lower() for d in district_filter)
        gj["features"] = [
            f for f in gj["features"]
            if _district_name(f).lower() in keep
        ]

    # Write to /tmp
    try:
        with open(tmp, "w") as f:
            json.dump(gj, f)
    except Exception:
        pass

    _geom_cache[city_key] = gj
    return gj


def _district_name(feature):
    """Extract district name from a variety of property key names."""
    p = feature.get("properties", {})
    for key in ("DISTRICT", "District", "district", "NAME_2", "dtname", "Dist_Name"):
        if key in p and p[key]:
            return str(p[key])
    return ""


def get_zone_ids(city_key):
    """Return list of zone IDs (ward numbers or district names) for a city."""
    gj = get_city_geojson(city_key)
    cfg = CITIES.get(city_key, {})
    ids = []
    if cfg.get("use_local_wards"):
        for f in gj["features"]:
            w = f["properties"].get("ward") or f["properties"].get("Ward_No", "")
            if w:
                ids.append(str(w))
    else:
        for f in gj["features"]:
            ids.append(_district_name(f) or str(f.get("id", "")))
    return ids


def build_indicator_geojson(city_key, rows, indicator="lst"):
    """
    Merge indicator rows into a GeoJSON FeatureCollection.
    rows: list of dicts with keys zone_id, lst, ndvi, ndbi, rainfall, trend, zone_name
    """
    gj = get_city_geojson(city_key)
    cfg = CITIES.get(city_key, {})
    use_wards = cfg.get("use_local_wards", False)

    # Build lookup: zone_id → row
    row_map = {}
    for r in rows:
        row_map[str(r["zone_id"])] = r

    features = []
    for feat in gj["features"]:
        if use_wards:
            zid = str(feat["properties"].get("ward") or feat["properties"].get("Ward_No", ""))
        else:
            zid = _district_name(feat)

        row = row_map.get(zid, {})
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
            "indicator_value": round(val, 4),
        }
        features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": features}
