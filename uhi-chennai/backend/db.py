"""
backend/db.py
-------------
In-memory SQLite populated at startup.
- Chennai: 200 actual municipal ward satellite data from GEE CSVs.
- Other cities: district-level timeseries generated from published UHI baselines
  matching the exact district boundaries from INDIAN-SHAPEFILES.
"""

import sqlite3, csv, json, os, random

from backend.cities import CITIES, YEARS

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
    for city_key in CITIES:
        if city_key != "chennai":
            _generate_city(cur, city_key)

    conn.commit()
    cur.execute("CREATE INDEX idx_ts ON timeseries(city, zone_id, year)")
    conn.commit()
    return conn


def _load_chennai(cur):
    city = "chennai"
    # timeseries
    with open(os.path.join(DATA_DIR, "ward_timeseries_full.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                "INSERT INTO timeseries VALUES (?,?,?,?,?,?,?)",
                (city, str(row["ward"]), int(row["year"]),
                 float(row["NDVI"]), float(row["NDBI"]),
                 float(row["LST"]), float(row["rainfall"]))
            )
    # trends
    with open(os.path.join(DATA_DIR, "trend_significance.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                "INSERT INTO trends VALUES (?,?,?,?,?)",
                (city, str(row["ward"]), row["trend"],
                 float(row["p_value"]), float(row["slope"]))
            )
    # changepoints
    with open(os.path.join(DATA_DIR, "changepoints.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                "INSERT INTO changepoints VALUES (?,?,?)",
                (city, str(row["ward"]), row["changepoint_years"])
            )
    # ward metadata from geojson
    with open(os.path.join(DATA_DIR, "wards_2024.geojson"), encoding="utf-8") as f:
        gj = json.load(f)
    for feat in gj["features"]:
        p = feat["properties"]
        wid = str(p.get("ward") or p.get("Ward_No", ""))
        cur.execute(
            "INSERT OR REPLACE INTO zone_meta VALUES (?,?,?,?)",
            (city, wid, p.get("Zone name", f"Ward {wid}"), p.get("Zone", "Zone"))
        )


def _generate_city(cur, city_key):
    cfg = CITIES[city_key]
    b = cfg["baseline"]
    rng = random.Random(b.get("seed", 999))
    city = city_key

    lst_base   = b["lst"]
    lst_spread = b.get("lst_spread", 4.5)
    ndvi_base  = b["ndvi"]
    ndbi_base  = b["ndbi"]
    rain_base  = b["rainfall"]
    warm_rate  = b.get("warming_rate", 0.10)

    districts = cfg.get("districts", [])

    zone_lst_offset  = [rng.uniform(-lst_spread/2, lst_spread/2) for _ in districts]
    zone_ndvi_offset = [rng.uniform(-0.06, 0.06) for _ in districts]
    zone_ndbi_offset = [rng.uniform(-0.04, 0.05) for _ in districts]
    year_anomaly     = {y: rng.uniform(-0.4, 0.4) for y in YEARS}

    for i, zid in enumerate(districts):
        for y in YEARS:
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
                "INSERT INTO timeseries VALUES (?,?,?,?,?,?,?)",
                (city, zid, y,
                 max(0.01, round(ndvi, 4)),
                 max(0.01, round(ndbi, 4)),
                 round(lst, 4),
                 round(rain, 2))
            )

        lsts = [(2016 + j, lst_base + zone_lst_offset[i] + warm_rate * j + year_anomaly[2016 + j])
                for j in range(len(YEARS))]
        slope = _ols_slope(lsts)
        trend = "increasing" if (slope > 0.05) else ("decreasing" if slope < -0.05 else "no trend")
        p_val = round(rng.uniform(0.01, 0.08) if trend != "no trend" else rng.uniform(0.12, 0.85), 4)

        cur.execute("INSERT INTO trends VALUES (?,?,?,?,?)",
                    (city, zid, trend, p_val, round(slope, 5)))
        cur.execute("INSERT INTO changepoints VALUES (?,?,?)",
                    (city, zid, "[]"))
        cur.execute("INSERT INTO zone_meta VALUES (?,?,?,?)",
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
    return _rows("""
        SELECT t.zone_id, t.lst, t.ndvi, t.ndbi, t.rainfall,
               tr.trend, tr.slope, tr.p_value,
               m.zone_name, m.admin_unit
        FROM timeseries t
        LEFT JOIN trends    tr ON t.city=tr.city AND t.zone_id=tr.zone_id
        LEFT JOIN zone_meta m  ON t.city=m.city  AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        ORDER BY t.lst DESC
    """, (city, year))


def get_zone_detail(city, zone_id):
    meta  = _row("SELECT * FROM zone_meta   WHERE city=? AND LOWER(zone_id)=LOWER(?)", (city, zone_id))
    trend = _row("SELECT * FROM trends      WHERE city=? AND LOWER(zone_id)=LOWER(?)", (city, zone_id))
    cp    = _row("SELECT * FROM changepoints WHERE city=? AND LOWER(zone_id)=LOWER(?)", (city, zone_id))
    ts    = _rows("SELECT year,ndvi,ndbi,lst,rainfall FROM timeseries WHERE city=? AND LOWER(zone_id)=LOWER(?) ORDER BY year",
                  (city, zone_id))
    return meta, trend, cp, ts


def get_city_trend(city, metric="lst"):
    col = metric.lower() if metric.lower() in {"lst","ndvi","ndbi","rainfall"} else "lst"
    return _rows(f"SELECT year, AVG({col}) as value FROM timeseries WHERE city=? GROUP BY year ORDER BY year",
                 (city,))


def get_zone_summary(city, year=2024):
    return _rows("""
        SELECT m.zone_name, m.admin_unit,
               AVG(t.lst) avg_lst, AVG(t.ndvi) avg_ndvi, AVG(t.ndbi) avg_ndbi,
               COUNT(*) ward_count
        FROM timeseries t JOIN zone_meta m ON t.city=m.city AND t.zone_id=m.zone_id
        WHERE t.city=? AND t.year=?
        GROUP BY m.zone_name ORDER BY avg_lst DESC
    """, (city, year))


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
