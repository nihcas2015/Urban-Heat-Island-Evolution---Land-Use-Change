# Chennai Urban Heat Island Monitor

> A full-stack geospatial analytics platform for tracking Urban Heat Island evolution across Chennai's 200 municipal wards from 2016 to 2024.

---

## Why This Matters

Rapid urbanisation in Chennai has replaced permeable surfaces and vegetation with impervious built-up cover — roads, rooftops, concrete. The consequence is a measurable and growing Urban Heat Island (UHI) effect: the urban core runs persistently hotter than the surrounding rural periphery, intensifying heat exposure for residents, elevating cooling energy demand, and compounding climate vulnerability in a city already facing extreme heat stress.

Most existing analyses produce a static snapshot — a single-year heat map. This platform takes a **longitudinal, ward-level view** using sequential mining methods to answer richer questions:

- *Which wards are warming, and at what rate?*
- *Did any wards experience a sudden structural shift — a change-point — in their LST regime?*
- *How much of LST variation is explained by vegetation loss (NDVI) versus built-up expansion (NDBI)?*

The results are served through a **REST API and interactive dashboard**, making the data queryable and reproducible beyond a static report.

---

## Data Sources

| Source | Variables | Coverage |
|---|---|---|
| **Sentinel-2 Surface Reflectance** (ESA Copernicus, via GEE) | NDVI, NDBI | 2016–2024, annual median composites |
| **Landsat-8/9 Collection 2** (USGS/NASA, via GEE) | Land Surface Temperature (LST) | 2016–2024 |
| **Chennai Corporation Ward Boundaries** | Ward geometry, zone metadata | 200 wards |

All satellite data was processed in Google Earth Engine. Annual cloud-free median composites were generated and zonal statistics extracted per ward using `reduceRegions()`.

---

## Methods

### 1 — Spatial Aggregation
Ward-level mean values of LST, NDVI, NDBI, and rainfall were extracted for each year (2016–2024) from annual satellite composites. This produces a panel of 200 wards × 9 years = 1,800 ward-year observations.

### 2 — Mann-Kendall Trend Test
Non-parametric monotonic trend detection applied to each ward's 9-year LST series. Identifies wards with statistically significant warming or cooling at α = 0.05, without assumptions about the distribution of residuals.

### 3 — PELT Change-point Detection
The Pruned Exact Linear Time algorithm (PELT) applied via `ruptures` identifies structural breaks in each ward's LST series — years of sudden regime shift, typically coinciding with rapid land-use change events such as large development projects or mass deforestation.

### 4 — OLS Regression
Pooled ordinary least squares regression of LST on NDVI, NDBI, and rainfall across all ward-year observations. Reveals the relative contribution of each driver to heat intensity. R² = 0.17 at ward scale — expected, as ward-mean averaging smooths sub-ward micro-climate gradients.

---

## Key Findings

- **Peak LST (2024):** 42.9°C — Ward 146 (Manali zone)
- **City average LST (2024):** ~39.4°C
- **NDBI effect:** +23.5°C per unit — over 4× stronger than NDVI's cooling effect (+5.7°C), indicating that built-up expansion outpaces vegetation-based heat mitigation
- **Trend significance:** The 9-year series is near the lower bound for robust Mann-Kendall detection; extending to 2030+ will sharpen sensitivity

---

## API

The platform exposes a versioned REST API at `/api/v1/`. Interactive documentation is available at `/api/docs` (Swagger UI) and `/api/redoc`.

**Ward endpoints**
```
GET /api/v1/wards                         # Paginated ward list with indicator values
GET /api/v1/wards/{id}                    # Full timeseries + trend + change-point for one ward
GET /api/v1/wards/geojson?year=&indicator= # GeoJSON FeatureCollection for map rendering
```

**Analytics endpoints**
```
GET /api/v1/analytics/city-trend?metric=  # City-wide annual average for any indicator
GET /api/v1/analytics/zones               # Zone-level aggregation
GET /api/v1/analytics/rankings            # Top wards by indicator
GET /api/v1/analytics/distribution        # LST/NDVI/NDBI histogram buckets
GET /api/v1/analytics/regression          # Model coefficients, R², interpretation
```

---

## Stack

**Backend:** Python · FastAPI · SQLite (in-memory) · Pydantic  
**Frontend:** Vanilla JS (ES5) · Leaflet.js · Chart.js  
**Data processing:** Google Earth Engine · GeoPandas · pymannkendall · ruptures · scikit-learn  
**Deployment:** Vercel (Python serverless + static)

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API server
uvicorn api.index:app --reload --port 8000

# 3. Open the dashboard
#    Navigate to http://localhost:8000 in your browser
#    API docs at http://localhost:8000/api/docs
```

---

## Deployment (Vercel)

Push this repository to GitHub, then import it on [vercel.com](https://vercel.com). Vercel auto-detects the configuration and routes `/api/*` to the Python serverless function and all other paths to the static frontend.

---

## Extending This Platform

The architecture is deliberately minimal and extensible:

- **More cities:** Swap the ward GeoJSON and re-run the GEE pipeline for any city
- **Live data ingestion:** Replace the static data layer with a scheduled GEE export job (Cloud Scheduler + Cloud Storage) to keep the platform current
- **Sub-ward resolution:** Replace ward polygons with building-level or grid-level geometries for finer spatial granularity
- **Forecasting:** Add a Prophet or LSTM-based LST forecast endpoint using the existing timeseries
- **Authentication:** Add OAuth2 via FastAPI's security utilities for restricted data tiers

---

*Satellite imagery: Sentinel-2 (ESA Copernicus) · Landsat-8/9 (USGS/NASA) · Processed via Google Earth Engine*

