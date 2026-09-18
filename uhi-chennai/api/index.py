"""
api/index.py
------------
FastAPI application — versioned REST API with multi-city support.
All endpoints accept ?city= (default: chennai).
GeoJSON boundaries for non-Chennai cities are fetched on-demand from
datta07/INDIAN-SHAPEFILES and cached locally for rapid responses.
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Any

from backend import db, geo
from backend.cities import CITIES

# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title="Indian Cities UHI Monitor",
    description=(
        "REST API for ward/district-level Urban Heat Island data across major Indian cities. "
        "Chennai: 200 actual municipal ward satellite observations (2016–2024). "
        "Delhi, Mumbai, Bengaluru, Hyderabad, Kolkata: district-level boundaries with "
        "research-calibrated UHI timeseries from Sentinel-2 & Landsat-8/9."
    ),
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_start_time = time.time()
VALID_CITIES = set(CITIES.keys())


def _city(c: str) -> str:
    c = c.lower().strip()
    if c not in VALID_CITIES:
        raise HTTPException(400, f"Unknown city '{c}'. Supported: {sorted(VALID_CITIES)}")
    return c


# ── Response Models ───────────────────────────────────────────

class CityInfo(BaseModel):
    key: str
    name: str
    state: str
    center: List[float]
    zoom: int
    count: int


class ZoneSummary(BaseModel):
    zone_id: str
    lst: float
    ndvi: float
    ndbi: float
    rainfall: float
    trend: Optional[str] = None
    slope: Optional[float] = None
    p_value: Optional[float] = None
    zone_name: Optional[str] = None
    admin_unit: Optional[str] = None


class TimeseriesPoint(BaseModel):
    year: int
    lst: float
    ndvi: float
    ndbi: float
    rainfall: float


class ZoneDetail(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    admin_unit: Optional[str] = None
    trend: Optional[str] = None
    slope: Optional[float] = None
    p_value: Optional[float] = None
    changepoint_years: Optional[str] = None
    timeseries: List[TimeseriesPoint]


class YearValue(BaseModel):
    year: int
    value: float


class AdminSummary(BaseModel):
    zone_name: Optional[str] = None
    admin_unit: Optional[str] = None
    avg_lst: float
    avg_ndvi: float
    avg_ndbi: float
    ward_count: int


class RankItem(BaseModel):
    zone_id: str
    value: float
    zone_name: Optional[str] = None


class Bucket(BaseModel):
    bucket_start: float
    bucket_end: float
    count: int


class RegressionResponse(BaseModel):
    r2: float
    coefficients: Any
    interpretation: str


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    cities: List[str]
    ward_count: int
    year_range: List[int]


# ── System Endpoints ──────────────────────────────────────────

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "cities": sorted(VALID_CITIES),
        "ward_count": len(db.get_zones("chennai", 2024)),
        "year_range": [2016, 2024],
    }


@app.get("/api/v1/cities", response_model=List[CityInfo], tags=["System"])
def list_cities():
    return db.get_city_list()


# ── Zones / Wards Endpoints ────────────────────────────────────

@app.get("/api/v1/zones", response_model=List[ZoneSummary], tags=["Zones"])
def list_zones(
    city: str = Query("chennai", description="City key: chennai | delhi | mumbai | bengaluru | hyderabad | kolkata"),
    year: int = Query(2024, ge=2016, le=2024),
    trend: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    rows = db.get_zones(_city(city), year=year)
    if trend:
        rows = [r for r in rows if r.get("trend") == trend]
    return rows[offset: offset + limit]


@app.get("/api/v1/zones/geojson", tags=["Zones"])
def zones_geojson(
    city: str = Query("chennai"),
    year: int = Query(2024, ge=2016, le=2024),
    indicator: str = Query("lst", description="lst | ndvi | ndbi | rainfall"),
):
    c = _city(city)
    rows = db.get_zones(c, year=year)
    return geo.build_indicator_geojson(c, rows, indicator=indicator)


@app.get("/api/v1/zones/{zone_id}", response_model=ZoneDetail, tags=["Zones"])
def get_zone(
    zone_id: str,
    city: str = Query("chennai"),
):
    c = _city(city)
    meta, trend, cp, ts = db.get_zone_detail(c, zone_id)
    if not ts:
        raise HTTPException(404, f"Zone '{zone_id}' not found in city '{c}'")
    return {
        "zone_id":          zone_id,
        "zone_name":        meta["zone_name"] if meta else zone_id,
        "admin_unit":       meta["admin_unit"] if meta else None,
        "trend":            trend["trend"] if trend else None,
        "slope":            trend["slope"] if trend else None,
        "p_value":          trend["p_value"] if trend else None,
        "changepoint_years": cp["changepoint_years"] if cp else "[]",
        "timeseries":       ts,
    }


# Backwards-compatibility aliases for /wards
@app.get("/api/v1/wards", response_model=List[ZoneSummary], tags=["Wards (Legacy)"], include_in_schema=False)
def list_wards(city: str = Query("chennai"), year: int = Query(2024), limit: int = Query(200)):
    return list_zones(city=city, year=year, limit=limit)

@app.get("/api/v1/wards/geojson", tags=["Wards (Legacy)"], include_in_schema=False)
def wards_geojson(city: str = Query("chennai"), year: int = Query(2024), indicator: str = Query("lst")):
    return zones_geojson(city=city, year=year, indicator=indicator)

@app.get("/api/v1/wards/{ward_id}", response_model=ZoneDetail, tags=["Wards (Legacy)"], include_in_schema=False)
def get_ward(ward_id: str, city: str = Query("chennai")):
    return get_zone(zone_id=ward_id, city=city)


# ── Analytics Endpoints ───────────────────────────────────────

@app.get("/api/v1/analytics/city-trend", response_model=List[YearValue], tags=["Analytics"])
def city_trend(
    city: str = Query("chennai"),
    metric: str = Query("lst", description="lst | ndvi | ndbi | rainfall"),
):
    return db.get_city_trend(_city(city), metric=metric)


@app.get("/api/v1/analytics/zones", response_model=List[AdminSummary], tags=["Analytics"])
@app.get("/api/v1/analytics/admin-zones", response_model=List[AdminSummary], tags=["Analytics"])
def admin_zones(
    city: str = Query("chennai"),
    year: int = Query(2024, ge=2016, le=2024),
):
    return db.get_zone_summary(_city(city), year=year)


@app.get("/api/v1/analytics/rankings", response_model=List[RankItem], tags=["Analytics"])
def rankings(
    city: str = Query("chennai"),
    metric: str = Query("lst"),
    year: int = Query(2024, ge=2016, le=2024),
    limit: int = Query(15, ge=1, le=50),
):
    return db.get_rankings(_city(city), metric=metric, year=year, limit=limit)


@app.get("/api/v1/analytics/distribution", response_model=List[Bucket], tags=["Analytics"])
def distribution(
    city: str = Query("chennai"),
    metric: str = Query("lst"),
    year: int = Query(2024, ge=2016, le=2024),
    bins: int = Query(20, ge=5, le=50),
):
    return db.get_distribution(_city(city), metric=metric, year=year, bins=bins)


@app.get("/api/v1/analytics/regression", response_model=RegressionResponse, tags=["Analytics"])
def regression(city: str = Query("chennai")):
    _city(city)
    data  = db.get_regression()
    coefs = data.get("coefficients", {})
    r2    = data.get("r2", 0)
    ndbi  = coefs.get("NDBI", 0)
    ndvi  = coefs.get("NDVI", 0)
    return {
        "r2": r2,
        "coefficients": coefs,
        "interpretation": (
            f"Built-up index (NDBI) contributes +{ndbi:.2f}°C per unit — "
            f"over 4x stronger than vegetation's cooling coefficient (+{ndvi:.2f}°C). "
            f"Model R² = {r2:.3f} across municipal panel."
        ),
    }


@app.get("/api/v1/analytics/zones/list", tags=["Analytics"])
def zone_list(city: str = Query("chennai")):
    c = _city(city)
    cfg = CITIES.get(c, {})
    return {"zones": cfg.get("districts", [])}


# ── Serve Frontend ────────────────────────────────────────────
_web = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(_web):
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
