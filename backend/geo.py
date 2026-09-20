"""
backend/geo.py
--------------
Dynamic vector boundary loader and choropleth builder.
- Chennai: loads actual 200-ward municipal GeoJSON
- All India: loads 37 States & Union Territories from datta07/INDIAN-SHAPEFILES
- Any State: fetches all district boundaries on-demand from GitHub raw
Cached in memory and local filesystem/tmp.
Embedded vector boundary loader and choropleth builder.
All boundary data is embedded locally in data/geojson/ for instant offline/serverless loading:
- National: 37 States & Union Territories
- Metropolitan Cities: 20 major Indian cities with actual municipal wards
- States: 37 States with administrative districts
"""

import json
import os
import urllib.request
import time
from backend.cities import get_scope_info

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
GEOJSON_DIR = os.path.join(DATA_DIR, "geojson")

# In-memory GeoJSON cache
_geom_cache = {}


def _entity_name(feature):
    """Extract subdistrict/district/state/ward name from various GeoJSON property conventions."""
    """Extract ward/district/state name from various GeoJSON property conventions."""
    p = feature.get("properties", {})
    for key in ("sdtname", "SUB_DIST", "subdistrict", "TEHSIL", "TALUK", "dtname", "DISTRICT",
                "District", "district", "STNAME", "STNAME_SH", "ward", "Ward_No", "NAME_1",
                "NAME_2", "Dist_Name", "dt_name"):
    for key in (
        "wardname", "WARD_NAME", "ward", "Ward_No", "WARD_NO", "Name", "name",
        "dtname", "DISTRICT", "District", "district", "Dist_Name", "dt_name",
        "sdtname", "SUB_DIST", "subdistrict", "TEHSIL", "TALUK",
        "STNAME", "STNAME_SH", "NAME_1", "NAME_2", "objectid", "id"
    ):
        val = p.get(key)
        if val is not None and str(val).strip():
        if val is not None and str(val).strip() and str(val).strip() != "None":
            return str(val).strip()
    return str(feature.get("id", ""))


def get_city_geojson(scope_key):
    """Return filtered district/state GeoJSON for any territorial scope."""
    """Return local GeoJSON for any national, metropolitan, or state scope."""
    cfg = get_scope_info(scope_key)
    slug = cfg["key"]

    if slug in _geom_cache:
        return _geom_cache[slug]

    if cfg.get("use_local_wards"):
        # Chennai: 200 actual municipal ward polygons
        file_path = os.path.join(DATA_DIR, "wards_2024.geojson")
        with open(file_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
        _geom_cache[slug] = gj
        return gj
    # 1. National Overview
    if slug == "india":
        p = os.path.join(GEOJSON_DIR, "india_states.geojson")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                gj = json.load(f)
            _geom_cache[slug] = gj
            return gj

    # Check /tmp cache on serverless runtime
    cache_name = "india_states.json" if cfg.get("is_national") else f"{slug}_subdistricts.json"
    tmp_cache = os.path.join("/tmp", cache_name)
    # 2. Metropolitan City (Municipal Wards)
    if cfg.get("is_metro"):
        p = os.path.join(GEOJSON_DIR, "metros", f"{slug}.geojson")
        if not os.path.exists(p) and slug == "chennai":
            p = os.path.join(DATA_DIR, "wards_2024.geojson")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                gj = json.load(f)
            _geom_cache[slug] = gj
            return gj

    if os.path.exists(tmp_cache):
        try:
            with open(tmp_cache, "r", encoding="utf-8") as f:
    # 3. State Scope (Districts)
    slug_alt = slug.replace("_&_", "_").replace("&", "").strip("_")
    for s in (slug, slug_alt):
        p = os.path.join(GEOJSON_DIR, "states", f"{s}.geojson")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                gj = json.load(f)
            _geom_cache[slug] = gj
            return gj
        except Exception:
            pass

    # Remote fetch from GitHub raw (datta07/INDIAN-SHAPEFILES)
    url = cfg.get("geojson_url")
    if not url:
        return {"type": "FeatureCollection", "features": []}
    # Fallback: check if in metros or states by direct file match
    for sub in ("metros", "states"):
        for s in (slug, slug_alt):
            candidate = os.path.join(GEOJSON_DIR, sub, f"{s}.geojson")
            if os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    gj = json.load(f)
                _geom_cache[slug] = gj
                return gj

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UHI-Platform/2.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            gj = json.loads(r.read().decode("utf-8"))
    return {"type": "FeatureCollection", "features": []}

        try:
            with open(tmp_cache, "w", encoding="utf-8") as f:
                json.dump(gj, f)
        except Exception:
            pass

        _geom_cache[slug] = gj
        return gj
    except Exception as e:
        print(f"Error fetching GeoJSON for {slug}: {e}")
        return {"type": "FeatureCollection", "features": []}


def get_zone_ids(scope_key):
    """Return ordered list of zone/district/state names for a territory."""
    """Return ordered list of unique zone/ward/district names for a territory."""
    gj = get_city_geojson(scope_key)
    cfg = get_scope_info(scope_key)
    ids = []
    if cfg.get("use_local_wards"):
        for f in gj.get("features", []):
            w = f["properties"].get("ward") or f["properties"].get("Ward_No", "")
            if w:
                ids.append(str(w))
    else:
        for f in gj.get("features", []):
            name = _entity_name(f)
            if name:
                ids.append(name)
    seen = set()
    for f in gj.get("features", []):
        name = _entity_name(f)
        if name and name not in seen:
            seen.add(name)
            ids.append(name)
    return ids


def build_indicator_geojson(scope_key, rows, indicator="lst"):
    """
    Merge indicator rows into GeoJSON features with multi-field property matching.
    Merge indicator rows into GeoJSON features with fuzzy property matching.
    rows: list of dicts with keys zone_id, lst, ndvi, ndbi, rainfall, trend, slope, zone_name
    """
    gj = get_city_geojson(scope_key)
    cfg = get_scope_info(scope_key)
    use_wards = cfg.get("use_local_wards", False)

    row_map = {str(r["zone_id"]).lower(): r for r in rows}

    features = []
    for feat in gj.get("features", []):
        if use_wards:
            raw_zid = str(feat["properties"].get("ward") or feat["properties"].get("Ward_No", ""))
        else:
            raw_zid = _entity_name(feat)
        raw_zid = _entity_name(feat)
        row = row_map.get(raw_zid.lower())

        row = row_map.get(raw_zid.lower())
        if not row:
            for k, v in row_map.items():
                if k in raw_zid.lower() or raw_zid.lower() in k:
                    row = v
                    break
        row = row or {}

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
