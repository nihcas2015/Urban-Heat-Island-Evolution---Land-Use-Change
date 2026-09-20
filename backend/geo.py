"""
backend/geo.py
--------------
Embedded vector boundary loader and choropleth builder.
All boundary data is embedded locally in data/geojson/ for instant loading:
- National: 37 States & Union Territories
- Metropolitan Cities: 20 major Indian cities with actual municipal wards
- States: 37 States with administrative districts
"""

import json
import os
from backend.cities import get_scope_info

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
GEOJSON_DIR = os.path.join(DATA_DIR, "geojson")

# In-memory GeoJSON cache
_geom_cache = {}


def _entity_name(feature):
    """Extract ward/district/state name from various GeoJSON property conventions."""
    p = feature.get("properties", {})
    for key in (
        "wardname", "WARD_NAME", "ward", "Ward_No", "WARD_NO", "Name", "name",
        "dtname", "DISTRICT", "District", "district", "Dist_Name", "dt_name",
        "sdtname", "SUB_DIST", "subdistrict", "TEHSIL", "TALUK",
        "STNAME", "STNAME_SH", "NAME_1", "NAME_2", "objectid", "id"
    ):
        val = p.get(key)
        if val is not None and str(val).strip() and str(val).strip() != "None":
            return str(val).strip()
    return str(feature.get("id", ""))


def get_city_geojson(scope_key):
    """Return local GeoJSON for any national, metropolitan, or state scope."""
    cfg = get_scope_info(scope_key)
    slug = cfg["key"]

    if slug in _geom_cache:
        return _geom_cache[slug]

    # 1. National Overview
    if slug == "india":
        p = os.path.join(GEOJSON_DIR, "india_states.geojson")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                gj = json.load(f)
            _geom_cache[slug] = gj
            return gj

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

    # 3. State Scope (Districts)
    slug_alt = slug.replace("_&_", "_").replace("&", "").strip("_")
    for s in (slug, slug_alt):
        p = os.path.join(GEOJSON_DIR, "states", f"{s}.geojson")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                gj = json.load(f)
            _geom_cache[slug] = gj
            return gj

    # Fallback: check if in metros or states by direct file match
    for sub in ("metros", "states"):
        for s in (slug, slug_alt):
            candidate = os.path.join(GEOJSON_DIR, sub, f"{s}.geojson")
            if os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    gj = json.load(f)
                _geom_cache[slug] = gj
                return gj

    return {"type": "FeatureCollection", "features": []}


def get_zone_ids(scope_key):
    """Return ordered list of unique zone/ward/district names for a territory."""
    gj = get_city_geojson(scope_key)
    ids = []
    seen = set()
    for f in gj.get("features", []):
        name = _entity_name(f)
        if name and name not in seen:
            seen.add(name)
            ids.append(name)
    return ids


def build_indicator_geojson(scope_key, rows, indicator="lst"):
    """
    Merge indicator rows into GeoJSON features with fuzzy property matching.
    rows: list of dicts with keys zone_id, lst, ndvi, ndbi, rainfall, trend, slope, zone_name
    """
    gj = get_city_geojson(scope_key)
    row_map = {str(r["zone_id"]).lower(): r for r in rows}

    features = []
    for feat in gj.get("features", []):
        raw_zid = _entity_name(feat)
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
