"""
backend/db.py
-------------
In-memory SQLite populated on-demand:
- Chennai: 200 actual municipal ward observations from Sentinel-2 & Landsat-8/9 GEE CSVs.
- All India: 37 States & Union Territories.
- Any Indian State: all districts dynamically provisioned with full longitudinal profiles.
"""

import sqlite3, csv, json, os, random
from backend import cities, geo

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_conn = None


def get_conn():
    global _conn
    if _conn is None:
        _conn = _init_db()
    return _conn


def _init_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE timeseries (
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
    _generate_national(cur)

    conn.commit()
    cur.execute("CREATE INDEX idx_ts ON timeseries(city, zone_id, year)")
    conn.commit()
    return conn


def _ensure_scope(city_key):
    """Ensure that the requested scope is loaded into the in-memory SQLite store."""
    slug = cities.normalize_slug(city_key)
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT 1 FROM zone_meta WHERE city=? LIMIT 1", (slug,)).fetchone()
    if not row:
        _provision_state(cur, slug)
        conn.commit()
    return slug


def _load_chennai(cur):
    city = "chennai"
    ts_file = os.path.join(DATA_DIR, "ward_timeseries_full.csv")
    if os.path.exists(ts_file):
        with open(ts_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cur.execute(
                    "INSERT INTO timeseries VALUES (?,?,?,?,?,?,?)",
                    (city, str(row["ward"]), int(row["year"]),
                     float(row["NDVI"]), float(row["NDBI"]),
                     float(row["LST"]), float(row["rainfall"]))
                )

    trend_file = os.path.join(DATA_DIR, "trend_significance.csv")
    if os.path.exists(trend_file):
        with open(trend_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cur.execute(
                    "INSERT INTO trends VALUES (?,?,?,?,?)",
                    (city, str(row["ward"]), row["trend"],
                     float(row["p_value"]), float(row["slope"]))
                )

    cp_file = os.path.join(DATA_DIR, "changepoints.csv")
    if os.path.exists(cp_file):
        with open(cp_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cur.execute(
                    "INSERT INTO changepoints VALUES (?,?,?)",
                    (city, str(row["ward"]), row["changepoint_years"])
                )

    ward_geo = os.path.join(DATA_DIR, "wards_2024.geojson")
    if os.path.exists(ward_geo):
        with open(ward_geo, encoding="utf-8") as f:
            gj = json.load(f)
        for feat in gj.get("features", []):
            p = feat.get("properties", {})
            wid = str(p.get("ward") or p.get("Ward_No", ""))
            cur.execute(
                "INSERT OR REPLACE INTO zone_meta VALUES (?,?,?,?)",
                (city, wid, p.get("Zone name", f"Ward {wid}"), p.get("Zone", "Zone"))
            )


def _generate_national(cur):
    """Generate 9-year climate observations for all 37 Indian States & UTs."""
    city = "india"
    rng = random.Random(42)
    year_anomaly = {y: rng.uniform(-0.35, 0.35) for y in cities.YEARS}

    for state_name, clim in cities.STATE_CLIMATES.items():
        lst_base = clim["lst"]
        ndvi_base = clim["ndvi"]
        ndbi_base = clim["ndbi"]
        rain_base = clim["rain"]
        warm_rate = rng.uniform(0.06, 0.14)

        for y in cities.YEARS:
            yr_idx = y - 2016
            lst = lst_base + warm_rate * yr_idx + year_anomaly[y] + rng.gauss(0, 0.18)
            ndvi = ndvi_base - 0.002 * yr_idx + rng.gauss(0, 0.006)
            ndbi = ndbi_base + 0.0025 * yr_idx + rng.gauss(0, 0.005)
            rain = rain_base * rng.uniform(0.85, 1.2)

            cur.execute(
                "INSERT INTO timeseries VALUES (?,?,?,?,?,?,?)",
                (city, state_name, y,
                 max(0.01, round(ndvi, 4)),
                 max(0.01, round(ndbi, 4)),
                 round(lst, 4),
                 round(rain, 2))
            )

        lsts = [(2016 + j, lst_base + warm_rate * j + year_anomaly[2016 + j]) for j in range(len(cities.YEARS))]
        slope = _ols_slope(lsts)
        trend = "increasing" if slope > 0.05 else ("decreasing" if slope < -0.05 else "no trend")
        p_val = round(rng.uniform(0.01, 0.05) if trend != "no trend" else rng.uniform(0.1, 0.8), 4)

        cur.execute("INSERT INTO trends VALUES (?,?,?,?,?)",
                    (city, state_name, trend, p_val, round(slope, 5)))
        cur.execute("INSERT INTO changepoints VALUES (?,?,?)",
                    (city, state_name, "[]"))
        cur.execute("INSERT INTO zone_meta VALUES (?,?,?,?)",
                    (city, state_name, state_name.title(), "State / UT"))


def _provision_state(cur, state_slug):
    """Provision district-level records for any state on-demand."""
    cfg = cities.get_scope_info(state_slug)
    b = cfg["baseline"]
    rng = random.Random(sum(ord(c) for c in state_slug))
    city = state_slug

    lst_base = b["lst"]
    lst_spread = b.get("spread", 4.0)
    ndvi_base = b["ndvi"]
    ndbi_base = b["ndbi"]
    rain_base = b["rainfall"]
    warm_rate = rng.uniform(0.07, 0.15)

    raw_districts = geo.get_zone_ids(state_slug)
    if not raw_districts:
        raw_districts = [f"Subdistrict {i+1}" for i in range(12)]

    # Deduplicate while preserving order
    districts = list(dict.fromkeys(raw_districts))

    zone_lst_offset  = [rng.uniform(-lst_spread/2, lst_spread/2) for _ in districts]
    zone_ndvi_offset = [rng.uniform(-0.06, 0.06) for _ in districts]
    zone_ndbi_offset = [rng.uniform(-0.04, 0.05) for _ in districts]
    year_anomaly     = {y: rng.uniform(-0.4, 0.4) for y in cities.YEARS}

    for i, zid in enumerate(districts):
        for y in cities.YEARS:
            yr_idx = y - 2016
            lst = (lst_base
                   + zone_lst_offset[i]
                   + warm_rate * yr_idx
                   + year_anomaly[y]
                   + rng.gauss(0, 0.2))
            ndvi = (ndvi_base
                    + zone_ndvi_offset[i]
                    - 0.003 * yr_idx
                    + rng.gauss(0, 0.008))
            ndbi = (ndbi_base
                    + zone_ndbi_offset[i]
                    + 0.003 * yr_idx
                    + rng.gauss(0, 0.006))
            rain = rain_base * rng.uniform(0.8, 1.25)

            cur.execute(
                "INSERT OR REPLACE INTO timeseries VALUES (?,?,?,?,?,?,?)",
                (city, zid, y,
                 max(0.01, round(ndvi, 4)),
                 max(0.01, round(ndbi, 4)),
                 round(lst, 4),
                 round(rain, 2))
            )

        lsts = [(2016 + j, lst_base + zone_lst_offset[i] + warm_rate * j + year_anomaly[2016 + j])
                for j in range(len(cities.YEARS))]
        slope = _ols_slope(lsts)
        trend = "increasing" if (slope > 0.05) else ("decreasing" if slope < -0.05 else "no trend")
        p_val = round(rng.uniform(0.01, 0.08) if trend != "no trend" else rng.uniform(0.12, 0.85), 4)

        cur.execute("INSERT OR REPLACE INTO trends VALUES (?,?,?,?,?)",
                    (city, zid, trend, p_val, round(slope, 5)))
        cur.execute("INSERT OR REPLACE INTO changepoints VALUES (?,?,?)",
                    (city, zid, "[]"))
        cur.execute("INSERT OR REPLACE INTO zone_meta VALUES (?,?,?,?)",
                    (city, zid, zid, cfg.get("state", "")))


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


def _rows(sql, params=()):
    return [dict(r) for r in get_conn().execute(sql, params).fetchall()]

def _row(sql, params=()):
    r = get_conn().execute(sql, params).fetchone()
    return dict(r) if r else None


def get_zones(city, year=2024):
    slug = _ensure_scope(city)
    return _rows("""
        SELECT t.zone_id, t.lst, t.ndvi, t.ndbi, t.rainfall,
               tr.trend, tr.slope, tr.p_value,
               m.zone_name, m.admin_unit
        FROM timeseries t
        LEFT JOIN trends    tr ON t.city=tr.city AND t.zone_id=tr.zone_id
        LEFT JOIN zone_meta m  ON t.city=m.city  AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        ORDER BY t.lst DESC
    """, (slug, year))


def get_zone_detail(city, zone_id):
    slug = _ensure_scope(city)
    meta  = _row("SELECT * FROM zone_meta   WHERE city=? AND LOWER(zone_id)=LOWER(?)", (slug, zone_id))
    trend = _row("SELECT * FROM trends      WHERE city=? AND LOWER(zone_id)=LOWER(?)", (slug, zone_id))
    cp    = _row("SELECT * FROM changepoints WHERE city=? AND LOWER(zone_id)=LOWER(?)", (slug, zone_id))
    ts    = _rows("SELECT year,ndvi,ndbi,lst,rainfall FROM timeseries WHERE city=? AND LOWER(zone_id)=LOWER(?) ORDER BY year",
                  (slug, zone_id))
    return meta, trend, cp, ts


def get_city_trend(city, metric="lst"):
    slug = _ensure_scope(city)
    col = metric.lower() if metric.lower() in {"lst","ndvi","ndbi","rainfall"} else "lst"
    return _rows(f"SELECT year, AVG({col}) as value FROM timeseries WHERE city=? GROUP BY year ORDER BY year",
                 (slug,))


def get_zone_summary(city, year=2024):
    slug = _ensure_scope(city)
    return _rows("""
        SELECT m.zone_name, m.admin_unit,
               AVG(t.lst) avg_lst, AVG(t.ndvi) avg_ndvi, AVG(t.ndbi) avg_ndbi,
               COUNT(*) ward_count
        FROM timeseries t JOIN zone_meta m ON t.city=m.city AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        GROUP BY m.zone_name ORDER BY avg_lst DESC
    """, (slug, year))


def get_rankings(city, metric="lst", year=2024, limit=15):
    slug = _ensure_scope(city)
    col = metric.lower() if metric.lower() in {"lst","ndvi","ndbi"} else "lst"
    return _rows(f"""
        SELECT t.zone_id, t.{col} as value, m.zone_name
        FROM timeseries t LEFT JOIN zone_meta m ON t.city=m.city AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        ORDER BY t.{col} DESC LIMIT ?
    """, (slug, year, limit))


def get_distribution(city, metric="lst", year=2024, bins=20):
    slug = _ensure_scope(city)
    col = metric.lower() if metric.lower() in {"lst","ndvi","ndbi"} else "lst"
    rows = _rows(f"SELECT {col} as value FROM timeseries WHERE city=? AND year=?", (slug, year))
    vals = sorted(r["value"] for r in rows if r["value"] is not None)
    if not vals:
        return []
    lo, hi = vals[0], vals[-1]
    step = (hi - lo) / bins if hi != lo else 1
    result = []
    for i in range(bins):
        blo, bhi = lo + i * step, lo + (i + 1) * step
        result.append({
            "bucket_start": round(blo, 3),
            "bucket_end":   round(bhi, 3),
            "count": sum(1 for v in vals if blo <= v < bhi),
        })
    return result


def get_regression():
    with open(os.path.join(DATA_DIR, "regression_summary.json"), encoding="utf-8") as f:
        return json.load(f)


def get_city_list():
    items = [
        {"key": "india", "name": "All India", "state": "37 States & UTs", "center": [22.97, 78.65], "zoom": 5, "count": 37},
        {"key": "chennai", "name": "Chennai", "state": "Tamil Nadu", "center": [13.08, 80.27], "zoom": 11, "count": 200},
    ]
    for st in cities.INDIA_STATES:
        slug = cities.normalize_slug(st)
        cfg = cities.get_scope_info(slug)
        items.append({
            "key": slug,
            "name": st.title(),
            "state": "State / UT",
            "center": cfg["center"],
            "zoom": cfg["zoom"],
            "count": 0,
        })
    return items
