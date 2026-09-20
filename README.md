# India Urban Heat Island & Climate Observatory

A full-stack, multi-scale geospatial surveillance system designed to monitor and analyze the longitudinal evolution of Urban Heat Islands (UHI) and land-use change across India. The platform processes high-resolution satellite imagery (Sentinel-2 and Landsat-8/9) to evaluate Land Surface Temperature (LST), Normalized Difference Vegetation Index (NDVI), and Normalized Difference Built-up Index (NDBI).

---

## Territorial Hierarchy

| Tier | Territorial Scope | Resolution & Entities | Data Source |
|---|---|---|---|
| **Tier 1 (National)** | All India | 37 States & Union Territories | S-2 / Landsat-8 Composites |
| **Tier 2 (State & Subdistricts)** | All 37 States/UTs | Comprehensive Subdistricts / Tehsils | Dynamic GeoJSON from `datta07/INDIAN-SHAPEFILES` |
| **Tier 3 (Municipal Wards)** | Greater Chennai Corporation | 200 Administrative Municipal Wards | Dedicated 9-Year Remote Sensing Panel |

---

## Scientific Indicators

- **Land Surface Temperature (LST):** Radiative surface temperature in °C derived from Landsat-8/9 Thermal Infrared Sensors (TIRS).
- **Normalized Difference Vegetation Index (NDVI):** Canopy density and green cover health derived from Sentinel-2 NIR & Red bands.
- **Normalized Difference Built-up Index (NDBI):** Concrete density and impervious surface footprint derived from Sentinel-2 SWIR & NIR bands.
- **Annual Rainfall:** Precipitation totals (mm) to contextualize seasonal variability.

---

## System Architecture

The architecture is zero-dependency on external paid APIs and operates out-of-the-box on serverless runtimes.

- **Backend:** Python 3.10+, FastAPI, SQLite (In-Memory), Pydantic
- **Spatial Processing:** GeoPandas, Google Earth Engine, `datta07/INDIAN-SHAPEFILES`
- **Analytics:** Mann-Kendall Trend Test (`pymannkendall`), Change-point Detection (`ruptures`), OLS Regression (`scikit-learn`)
- **Frontend:** Vanilla JavaScript, Leaflet.js, Chart.js, GPU-accelerated CSS
- **Deployment:** Vercel Serverless Function (`@vercel/python`) + Edge CDN

---

## Quickstart

### 1. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://localhost:8000` in your browser.
API documentation is available at `http://localhost:8000/api/docs`.

### 2. Zero-Cost Serverless Deployment (Vercel)

This repository includes `vercel.json` pre-configured for automatic serverless deployment:

1. Push this repository to GitHub.
2. Go to [vercel.com](https://vercel.com) and click **Add New Project**.
3. Import your GitHub repository.
4. Click **Deploy** (no build overrides or environment variables needed).

---

## API Endpoints

- `GET /api/v1/health` — System status, uptime, and supported territories.
- `GET /api/v1/cities` — Catalog of territorial scopes with coordinates and zoom levels.
- `GET /api/v1/zones?city={slug}&year={year}` — Indicator metrics for all features in scope.
- `GET /api/v1/zones/{zone_id}?city={slug}` — 9-year timeseries, Sen's slope, and change-point data.
- `GET /api/v1/zones/geojson?city={slug}&year={year}&indicator={metric}` — Choropleth GeoJSON.
- `GET /api/v1/analytics/city-trend?city={slug}&metric={metric}` — Aggregate longitudinal trend.
- `GET /api/v1/analytics/zones?city={slug}&year={year}` — Zone-level LST comparisons.
- `GET /api/v1/analytics/distribution?city={slug}&year={year}` — LST distribution histogram.
- `GET /api/v1/analytics/regression?city={slug}` — Multivariable OLS model summary.
- `GET /api/v1/analytics/rankings?city={slug}&year={year}&metric={metric}` — Ranked spatial features.

---

## License & Attribution

Distributed under the MIT License. Satellite data courtesy of the **European Space Agency (Copernicus Sentinel-2)** and **USGS/NASA (Landsat-8/9 Collection 2)**. Administrative boundary geometries sourced from open spatial repositories.
