"""
backend/db.py
-------------
Loads all source data into an in-memory SQLite database at startup.
All query functions return plain Python dicts/lists — no ORM.
In-memory SQLite populated at startup.
Chennai → real 200-ward satellite data from CSVs.
Other cities → research-calibrated synthetic district data, reproducibly
               generated from published UHI literature baselines.
All public functions return plain Python dicts.
- Chennai: 200 actual municipal ward satellite data from GEE CSVs.
- Other cities: district-level timeseries generated from published UHI baselines
  matching the exact district boundaries from INDIAN-SHAPEFILES.
"""

import sqlite3
import csv
import json
import os
import sqlite3, csv, json, os, random, math
import sqlite3, csv, json, os, random

# Module-level connection — created once per process lifetime
from backend.cities import CITIES, YEARS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_conn = None
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def get_conn():
    global _conn
    if _conn is None:
        _conn = _init_db()
    return _conn


# ── DB schema ────────────────────────────────────────────────────

def _init_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── timeseries ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE timeseries (
            ward    INTEGER,
            year    INTEGER,
            ndvi    REAL,
            ndbi    REAL,
            lst     REAL,
            city     TEXT,
            zone_id  TEXT,
            year     INTEGER,
            ndvi     REAL,
            ndbi     REAL,
            lst      REAL,
            rainfall REAL
        )
    """)
    cur.execute("""
        CREATE TABLE trends (
            city      TEXT,
            zone_id   TEXT,
            trend     TEXT,
            p_value   REAL,
            slope     REAL,
            PRIMARY KEY (city, zone_id)
        )
    """)
    cur.execute("""
        CREATE TABLE changepoints (
            city              TEXT,
            zone_id           TEXT,
            changepoint_years TEXT,
            PRIMARY KEY (city, zone_id)
        )
    """)
    cur.execute("""
        CREATE TABLE zone_meta (
            city       TEXT,
            zone_id    TEXT,
            zone_name  TEXT,
            admin_unit TEXT,
            PRIMARY KEY (city, zone_id)
        )
    """)

    _load_chennai(cur)
    for city_key in CITIES:
        if city_key != "chennai":
            _generate_city(cur, city_key)

    conn.commit()
    cur.execute("CREATE INDEX idx_ts ON timeseries(city, zone_id, year)")
    conn.commit()
    return conn


# ── Chennai: load real data ───────────────────────────────────────

def _load_chennai(cur):
    city = "chennai"
    # timeseries
    with open(os.path.join(DATA_DIR, "ward_timeseries_full.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
    with open(os.path.join(DATA_DIR, "ward_timeseries_full.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                "INSERT INTO timeseries VALUES (?,?,?,?,?,?)",
                (int(row["ward"]), int(row["year"]),
                "INSERT INTO timeseries VALUES (?,?,?,?,?,?,?)",
                (city, str(row["ward"]), int(row["year"]),
                 float(row["NDVI"]), float(row["NDBI"]),
                 float(row["LST"]), float(row["rainfall"]))
            )

    # ── trends ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE trends (
            ward    INTEGER PRIMARY KEY,
            trend   TEXT,
            p_value REAL,
            slope   REAL
        )
    """)
    # trends
    with open(os.path.join(DATA_DIR, "trend_significance.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
    with open(os.path.join(DATA_DIR, "trend_significance.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                "INSERT INTO trends VALUES (?,?,?,?)",
                (int(row["ward"]), row["trend"],
                "INSERT INTO trends VALUES (?,?,?,?,?)",
                (city, str(row["ward"]), row["trend"],
                 float(row["p_value"]), float(row["slope"]))
            )

    # ── changepoints ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE changepoints (
            ward              INTEGER PRIMARY KEY,
            changepoint_years TEXT
        )
    """)
    # changepoints
    with open(os.path.join(DATA_DIR, "changepoints.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
    with open(os.path.join(DATA_DIR, "changepoints.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                "INSERT INTO changepoints VALUES (?,?)",
                (int(row["ward"]), row["changepoint_years"])
                "INSERT INTO changepoints VALUES (?,?,?)",
                (city, str(row["ward"]), row["changepoint_years"])
            )

    # ── ward_meta: zone info from GeoJSON ───────────────────────
    cur.execute("""
        CREATE TABLE ward_meta (
            ward        INTEGER PRIMARY KEY,
            zone        TEXT,
            zone_no     INTEGER,
            zone_name   TEXT,
            city        TEXT
        )
    """)
    # ward metadata from geojson
    with open(os.path.join(DATA_DIR, "wards_2024.geojson")) as f:
    with open(os.path.join(DATA_DIR, "wards_2024.geojson"), encoding="utf-8") as f:
        gj = json.load(f)
    for feat in gj["features"]:
        p = feat["properties"]
        ward_id = int(p.get("ward", p.get("Ward_No", 0)))
        wid = str(p.get("ward") or p.get("Ward_No", ""))
        cur.execute(
            "INSERT OR REPLACE INTO ward_meta VALUES (?,?,?,?,?)",
            (ward_id,
             p.get("Zone", ""),
             int(p.get("Zone no", 0)),
             p.get("Zone name", ""),
             p.get("City", "Chennai"))
            "INSERT OR REPLACE INTO zone_meta VALUES (?,?,?,?)",
            (city, wid, p.get("Zone name", wid), p.get("Zone", ""))
            (city, wid, p.get("Zone name", f"Ward {wid}"), p.get("Zone", "Zone"))
        )

    conn.commit()

    # Indexes for fast lookups
    cur.execute("CREATE INDEX idx_ts_ward ON timeseries(ward)")
    cur.execute("CREATE INDEX idx_ts_year ON timeseries(year)")
    conn.commit()
    return conn
# ── Synthetic data for other cities ──────────────────────────────

def _generate_city(cur, city_key):
    """
    Generate plausible 9-year district-level timeseries using baselines from
    published UHI studies for each city. Seeded for reproducibility.
    Districts are fetched lazily by geo.py — here we generate the data
    using sequential zone IDs that will be matched to geometry at API time.
    """
    cfg = CITIES[city_key]
    b = cfg["baseline"]
    rng = random.Random(b.get("seed", 999))
    city = city_key

# ── Query functions ─────────────────────────────────────────────
    lst_base     = b["lst"]
    lst_spread   = b.get("lst_spread", 4.5)
    ndvi_base    = b["ndvi"]
    ndbi_base    = b["ndbi"]
    rain_base    = b["rainfall"]
    warm_rate    = b.get("warming_rate", 0.10)   # °C/yr city-wide trend
    lst_base   = b["lst"]
    lst_spread = b.get("lst_spread", 4.5)
    ndvi_base  = b["ndvi"]
    ndbi_base  = b["ndbi"]
    rain_base  = b["rainfall"]
    warm_rate  = b.get("warming_rate", 0.10)

def fetch_all(sql, params=()):
    cur = get_conn().execute(sql, params)
    return [dict(r) for r in cur.fetchall()]
    # Approximate number of districts for each city
    n_zones = {
        "delhi": 11, "mumbai": 5, "bengaluru": 5,
        "hyderabad": 5, "kolkata": 5,
    }.get(city_key, 8)
    districts = cfg.get("districts", [])

    # Per-zone static offsets (simulate land-cover variation)
    zone_ids = [str(i + 1) for i in range(n_zones)]
    zone_lst_offset  = [rng.uniform(-lst_spread/2, lst_spread/2) for _ in zone_ids]
    zone_ndvi_offset = [rng.uniform(-0.08, 0.08) for _ in zone_ids]
    zone_ndbi_offset = [rng.uniform(-0.05, 0.06) for _ in zone_ids]
    zone_lst_offset  = [rng.uniform(-lst_spread/2, lst_spread/2) for _ in districts]
    zone_ndvi_offset = [rng.uniform(-0.06, 0.06) for _ in districts]
    zone_ndbi_offset = [rng.uniform(-0.04, 0.05) for _ in districts]
    year_anomaly     = {y: rng.uniform(-0.4, 0.4) for y in YEARS}

def fetch_one(sql, params=()):
    cur = get_conn().execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None
    # Year-level city-wide anomaly (simulates inter-annual weather variability)
    year_anomaly = {y: rng.uniform(-0.6, 0.6) for y in YEARS}

    for i, zid in enumerate(zone_ids):
    for i, zid in enumerate(districts):
        for y in YEARS:
            yr_idx = y - 2016
            # LST: base + zone offset + city warming trend + year noise
            lst = (lst_base
                   + zone_lst_offset[i]
                   + warm_rate * yr_idx
                   + year_anomaly[y]
                   + rng.gauss(0, 0.3))
            # NDVI: slight decline over time (urbanisation)
                   + rng.gauss(0, 0.2))
            ndvi = (ndvi_base
                    + zone_ndvi_offset[i]
                    - 0.004 * yr_idx
                    + rng.gauss(0, 0.01))
            # NDBI: slight rise over time
                    - 0.003 * yr_idx
                    + rng.gauss(0, 0.008))
            ndbi = (ndbi_base
                    + zone_ndbi_offset[i]
                    + 0.003 * yr_idx
                    + rng.gauss(0, 0.008))
            # Rainfall: based on city type with inter-annual variability
            rain = rain_base * rng.uniform(0.75, 1.30)
                    + rng.gauss(0, 0.006))
            rain = rain_base * rng.uniform(0.8, 1.25)

def get_ward_ids():
    return [r["ward"] for r in fetch_all("SELECT DISTINCT ward FROM timeseries ORDER BY ward")]
            cur.execute(
                "INSERT INTO timeseries VALUES (?,?,?,?,?,?,?)",
                (city, zid, y,
                 max(0.0, round(ndvi, 4)),
                 max(0.0, round(ndbi, 4)),
                 max(0.01, round(ndvi, 4)),
                 max(0.01, round(ndbi, 4)),
                 round(lst, 4),
                 round(rain, 2))
            )

        # Compute slope and simple trend classification from the series
        lsts = [(2016 + j, lst_base + zone_lst_offset[i] + warm_rate * j + year_anomaly[2016 + j])
                for j in range(len(YEARS))]
        slope = _ols_slope(lsts)
        trend = "increasing" if (slope > 0.05) else ("decreasing" if slope < -0.05 else "no trend")
        p_val = round(rng.uniform(0.01, 0.15) if trend != "no trend" else rng.uniform(0.15, 0.95), 4)
        p_val = round(rng.uniform(0.01, 0.08) if trend != "no trend" else rng.uniform(0.12, 0.85), 4)

def get_ward_timeseries(ward_id):
    return fetch_all(
        "SELECT year, ndvi, ndbi, lst, rainfall FROM timeseries WHERE ward=? ORDER BY year",
        (ward_id,)
    )
        cur.execute("INSERT INTO trends VALUES (?,?,?,?,?)",
                    (city, zid, trend, p_val, round(slope, 5)))
        cur.execute("INSERT INTO changepoints VALUES (?,?,?)",
                    (city, zid, "[]"))
        cur.execute("INSERT INTO zone_meta VALUES (?,?,?,?)",
                    (city, zid, f"District {zid}", ""))
                    (city, zid, zid, cfg.get("state", "")))


def get_ward_trend(ward_id):
    return fetch_one("SELECT * FROM trends WHERE ward=?", (ward_id,))
def _ols_slope(xy_pairs):
    n = len(xy_pairs)
    if n < 2:
        return 0.0
    sx  = sum(x for x, _ in xy_pairs)
    sy  = sum(y for _, y in xy_pairs)
    sxy = sum(x * y for x, y in xy_pairs)
    sxx = sum(x * x for x, _ in xy_pairs)
    denom = n * sxx - sx * sx
    return (n * sxy - sx * sy) / denom if denom else 0.0


def get_ward_changepoint(ward_id):
    return fetch_one("SELECT * FROM changepoints WHERE ward=?", (ward_id,))
# ── Query helpers ─────────────────────────────────────────────────

def _rows(sql, params=()):
    return [dict(r) for r in get_conn().execute(sql, params).fetchall()]

def get_ward_meta(ward_id):
    return fetch_one("SELECT * FROM ward_meta WHERE ward=?", (ward_id,))
def _row(sql, params=()):
    r = get_conn().execute(sql, params).fetchone()
    return dict(r) if r else None


def get_wards_summary(year=2024):
    """Ward list with a single year's indicators + trend."""
    return fetch_all("""
        SELECT t.ward, t.lst, t.ndvi, t.ndbi, t.rainfall,
def get_zones(city, year=2024):
    return _rows("""
        SELECT t.zone_id, t.lst, t.ndvi, t.ndbi, t.rainfall,
               tr.trend, tr.slope, tr.p_value,
               m.zone_name, m.zone_no, m.zone
               m.zone_name, m.admin_unit
        FROM timeseries t
        LEFT JOIN trends tr ON t.ward = tr.ward
        LEFT JOIN ward_meta m ON t.ward = m.ward
        WHERE t.year = ?
        ORDER BY t.ward
    """, (year,))
        LEFT JOIN trends    tr ON t.city=tr.city AND t.zone_id=tr.zone_id
        LEFT JOIN zone_meta m  ON t.city=m.city  AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        ORDER BY t.lst DESC
    """, (city, year))


def get_city_trend(metric="lst"):
    allowed = {"lst", "ndvi", "ndbi", "rainfall"}
    col = metric.lower() if metric.lower() in allowed else "lst"
    return fetch_all(
        f"SELECT year, AVG({col}) as value FROM timeseries GROUP BY year ORDER BY year"
    )
def get_zone_detail(city, zone_id):
    meta  = _row("SELECT * FROM zone_meta   WHERE city=? AND zone_id=?", (city, zone_id))
    trend = _row("SELECT * FROM trends      WHERE city=? AND zone_id=?", (city, zone_id))
    cp    = _row("SELECT * FROM changepoints WHERE city=? AND zone_id=?", (city, zone_id))
    ts    = _rows("SELECT year,ndvi,ndbi,lst,rainfall FROM timeseries WHERE city=? AND zone_id=? ORDER BY year",
    meta  = _row("SELECT * FROM zone_meta   WHERE city=? AND LOWER(zone_id)=LOWER(?)", (city, zone_id))
    trend = _row("SELECT * FROM trends      WHERE city=? AND LOWER(zone_id)=LOWER(?)", (city, zone_id))
    cp    = _row("SELECT * FROM changepoints WHERE city=? AND LOWER(zone_id)=LOWER(?)", (city, zone_id))
    ts    = _rows("SELECT year,ndvi,ndbi,lst,rainfall FROM timeseries WHERE city=? AND LOWER(zone_id)=LOWER(?) ORDER BY year",
                  (city, zone_id))
    return meta, trend, cp, ts


def get_zone_summary(year=2024):
    return fetch_all("""
        SELECT m.zone_name, m.zone,
               AVG(t.lst) as avg_lst,
               AVG(t.ndvi) as avg_ndvi,
               AVG(t.ndbi) as avg_ndbi,
               COUNT(*) as ward_count
        FROM timeseries t
        JOIN ward_meta m ON t.ward = m.ward
        WHERE t.year = ?
        GROUP BY m.zone_name
        ORDER BY avg_lst DESC
    """, (year,))
def get_city_trend(city, metric="lst"):
    col = metric.lower() if metric.lower() in {"lst","ndvi","ndbi","rainfall"} else "lst"
    return _rows(f"SELECT year, AVG({col}) as value FROM timeseries WHERE city=? GROUP BY year ORDER BY year",
                 (city,))


def get_rankings(metric="lst", year=2024, limit=15):
    allowed = {"lst", "ndvi", "ndbi"}
    col = metric.lower() if metric.lower() in allowed else "lst"
    order = "DESC" if col in {"lst", "ndbi"} else "DESC"
    return fetch_all(f"""
        SELECT t.ward, t.{col} as value, m.zone_name
        FROM timeseries t
        LEFT JOIN ward_meta m ON t.ward = m.ward
        WHERE t.year = ?
        ORDER BY t.{col} {order}
        LIMIT ?
    """, (year, limit))
def get_zone_summary(city, year=2024):
    return _rows("""
        SELECT m.zone_name, m.admin_unit,
               AVG(t.lst) avg_lst, AVG(t.ndvi) avg_ndvi, AVG(t.ndbi) avg_ndbi,
               COUNT(*) ward_count
        FROM timeseries t JOIN zone_meta m ON t.city=m.city AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        GROUP BY m.zone_name ORDER BY avg_lst DESC
    """, (city, year))


def get_distribution(metric="lst", year=2024, bins=20):
    allowed = {"lst", "ndvi", "ndbi"}
    col = metric.lower() if metric.lower() in allowed else "lst"
    rows = fetch_all(f"SELECT {col} as value FROM timeseries WHERE year=?", (year,))
    vals = sorted(r["value"] for r in rows)
def get_rankings(city, metric="lst", year=2024, limit=15):
    col = metric.lower() if metric.lower() in {"lst","ndvi","ndbi"} else "lst"
    return _rows(f"""
        SELECT t.zone_id, t.{col} as value, m.zone_name
        FROM timeseries t LEFT JOIN zone_meta m ON t.city=m.city AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        ORDER BY t.{col} DESC LIMIT ?
    """, (city, year, limit))


def get_distribution(city, metric="lst", year=2024, bins=20):
    col = metric.lower() if metric.lower() in {"lst","ndvi","ndbi"} else "lst"
    rows = _rows(f"SELECT {col} as value FROM timeseries WHERE city=? AND year=?", (city, year))
    vals = sorted(r["value"] for r in rows if r["value"] is not None)
    if not vals:
        return []
    lo, hi = vals[0], vals[-1]
    step = (hi - lo) / bins if hi != lo else 1
    result = []
    for i in range(bins):
        bucket_lo = lo + i * step
        bucket_hi = lo + (i + 1) * step
        count = sum(1 for v in vals if bucket_lo <= v < bucket_hi)
        blo, bhi = lo + i * step, lo + (i + 1) * step
        result.append({
            "bucket_start": round(bucket_lo, 3),
            "bucket_end": round(bucket_hi, 3),
            "count": count
            "bucket_start": round(blo, 3),
            "bucket_end":   round(bhi, 3),
            "count": sum(1 for v in vals if blo <= v < bhi),
        })
    return result


def get_regression():
    with open(os.path.join(DATA_DIR, "regression_summary.json")) as f:
    with open(os.path.join(DATA_DIR, "regression_summary.json"), encoding="utf-8") as f:
        return json.load(f)


def get_city_list():
    return [
        {
            "key":    k,
            "name":   v["name"],
            "state":  v["state"],
            "center": v["center"],
            "zoom":   v["zoom"],
            "count":  len(v.get("districts", [])),
        }
        for k, v in CITIES.items()
    ]
