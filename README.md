# THERMALIS — National Urban Heat & Climate Observatory

An enterprise-grade, multi-scale geospatial surveillance system for monitoring and analyzing the longitudinal evolution of Urban Heat Islands (UHI) and land-use change across the Republic of India.

Powered by multi-decadal satellite remote sensing (Sentinel-2 MSI and Landsat-8/9 TIRS), THERMALIS delivers continuous microclimate intelligence across **All India (37 States & Union Territories)**, **all administrative districts**, and **20 major metropolitan corporations resolved down to individual municipal wards**.

---

## Executive Summary & Motivation

### The Problem
Over the past decade, rapid urbanization across India has drastically altered the surface energy balance. Replacing vegetative canopy and permeable soil with high-albedo, impervious infrastructure (concrete, bitumen, dense masonry) creates pronounced **Urban Heat Islands (UHI)**. Surface temperatures in urban cores frequently exceed peripheral rural baselines by **3°C to 7°C**, amplifying heat-wave mortality, placing strain on municipal water resources, and driving peak power grid demand.

### The Need
Municipal corporations, state climate disaster management authorities (SDMAs), and urban planners have historically relied on:
1. Coarse weather station networks that fail to capture localized hyper-thermal micro-hotspots.
2. Proprietary GIS toolkits with heavy desktop installation footprints, prohibitive licensing costs, and manual processing pipelines.
3. Third-party cloud APIs that impose rate limits, mandatory access tokens, and recurrent subscription costs.

### The Solution: THERMALIS
THERMALIS provides a completely open, high-performance, and zero-external-API-dependency climate observatory. It translates petabytes of raw Earth Observation telemetry into a sub-second, interactive exploration platform with:
- **Hierarchical Drilldown:** Smooth transitions from national aggregates to state districts and municipal wards.
- **Embedded Vector Geometries:** 58 pre-processed, simplified boundary datasets requiring zero runtime download.
- **Dual-Tier Resilient Architecture:** Operates with 100% uptime directly on static Edge CDNs with instant fallback if backend serverless runtimes experience cold starts.
- **Strict Accessibility & Performance:** Dark-mode interface (`#000000`), active kinetic cursor physics, zero AI emoji clutter, and GPU-accelerated 60 FPS rendering.

---

## Territorial Coverage & Hierarchy

| Tier | Administrative Scope | Geometries & Granularity | Source Attribution |
|---|---|---|---|
| **Tier 1: National** | All India | 37 States & Union Territories | Survey of India / LGD |
| **Tier 2: State & District** | All 37 States & UTs | Comprehensive Administrative Districts (e.g. 38 in Tamil Nadu, 36 in Maharashtra, 75 in UP) | Open Spatial Repositories (`datta07/INDIAN-SHAPEFILES`) |
| **Tier 3: Metropolitan Wards** | 20 Major Municipal Corporations | Individual Administrative Wards (Bengaluru: 197, Delhi: 261, Chennai: 200, Hyderabad: 150, Mumbai: 28, Jaipur: 149, Ahmedabad: 46, Pune: 42, etc.) | Municipal Spatial Portals (BBMP, MCD, GCC, GHMC, BMC, PMC, JMC) |

### Embedded Metropolitan Cities (20 Wards Geometries)
- **Southern Region:** Bengaluru (BBMP), Chennai (GCC), Hyderabad (GHMC), Visakhapatnam (GVMC)
- **Western Region:** Mumbai (BMC), Pune (PMC), Nagpur (NMC), Thane (TMC), Navi Mumbai (NMMC), Pimpri Chinchwad (PCMC), Ahmedabad (AMC), Surat (SMC), Vadodara (VMC)
- **Northern Region:** Delhi NCR (MCD), Jaipur (JMC), Lucknow (LMC), Kanpur (KMC)
- **Central & Eastern Region:** Bhopal (BMC), Indore (IMC), Patna (PMC)

---

## Core Scientific Indicators

THERMALIS synthesizes four critical environmental parameters across a 9-year longitudinal panel (2016–2024):

### 1. Land Surface Temperature (LST, °C)
Radiative skin temperature computed from Landsat-8/9 Thermal Infrared Sensors (TIRS Band 10) utilizing the Split-Window Algorithm and GEE Top-of-Atmosphere (TOA) radiance calibrations, adjusted for fractional vegetation cover emissivity:
$$\epsilon = \epsilon_v P_v + \epsilon_s (1 - P_v) + C$$

### 2. Normalized Difference Vegetation Index (NDVI)
Canopy density and vegetative health derived from Sentinel-2 MultiSpectral Instrument (MSI) Level-2A surface reflectance:
$$\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}} = \frac{B8 - B4}{B8 + B4}$$

### 3. Normalized Difference Built-Up Index (NDBI)
Impervious surface footprint, dense built masonry, and commercial infrastructure density:
$$\text{NDBI} = \frac{\text{SWIR} - \text{NIR}}{\text{SWIR} + \text{NIR}} = \frac{B11 - B8}{B11 + B8}$$

### 4. Annual Precipitation (mm)
Gridded annual precipitation estimates derived from CHIRPS and IMD reanalysis to evaluate precipitation attenuation against thermal trends.

### 5. Mann-Kendall Trend Test & Sen's Slope
Non-parametric monotonic trend detection evaluating longitudinal warming/cooling trajectories:
$$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \text{sgn}(x_j - x_k)$$
Sen's slope estimator is calculated to identify statutory significance at the $p < 0.05$ threshold.

---

## Technology Stack

```
Layer                  Technologies
──────────────────────────────────────────────────────────────────────────────
Geospatial Analytics   Google Earth Engine, GeoPandas, Shapely, PyMannKendall
Backend Runtime        Python 3.10+, FastAPI, Pydantic v2, Uvicorn, SQLite
Frontend Architecture  Vanilla ES6+, Leaflet.js 1.9.4, Chart.js 4.4.0
Interactive Graphics   HTML5 Canvas (Kinetic Cursor Physics, Elastic Spring Mesh)
Data Serialization     GeoJSON (Douglas-Peucker Simplified, EPSG:4326)
Cloud & Edge Infra     Vercel Serverless Functions (@vercel/python), Vercel Edge CDN
Style & Typography     Inter, JetBrains Mono, Custom SVG Aperture Iconography
```

---

## Repository Structure

```
.
├── api/
│   └── index.py                    # FastAPI application, routing, and static file mount
├── backend/
│   ├── __init__.py                 # Package initializer
│   ├── cities.py                   # 58-territory catalog, regional baselines, coordinate index
│   ├── db.py                       # In-memory SQLite engine & Chennai empirical timeseries loader
│   └── geo.py                      # Boundary loader, choropleth generator, feature normalizer
├── data/
│   ├── changepoints.csv            # Pelts offline changepoint detection outputs (2016-2024)
│   ├── regression_summary.json     # OLS multivariable regression summary (NDBI vs NDVI on LST)
│   ├── trend_significance.csv      # Mann-Kendall tau and p-values per administrative unit
│   ├── ward_timeseries_full.csv    # 9-year empirical satellite panel (200 Chennai GCC wards)
│   └── wards_2024.geojson          # High-resolution reference geometries for GCC
├── public/
│   ├── app.js                      # Core frontend: Leaflet drilldown, Kinetic canvas, Chart.js
│   ├── index.html                  # Main application interface (zero emojis, accessible markup)
│   ├── style.css                   # Obsidian dark theme (#000000), responsive grid, design system
│   └── data/
│       ├── catalog.json            # Pre-compiled metadata, bounds, and baselines for 58 entities
│       ├── chennai_data.json       # Pre-compiled 9-year timeseries for instant CDN delivery
│       └── geojson/
│           ├── india_states.geojson # National polygon collection (37 States & UTs)
│           ├── metros/             # 20 Metropolitan Municipal Wards (Bengaluru, Delhi, etc.)
│           └── states/             # 37 State boundary files resolved to administrative districts
├── .gitignore                      # Git exclusion rules (__pycache__, pyc, env, logs)
├── README.md                       # System architecture, scientific documentation, deployment guide
├── requirements.txt                # Python backend dependencies
└── vercel.json                     # Serverless function configuration and URL rewrite rules
```

---

## Local Development Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Standard modern browser (Chrome, Firefox, Safari, Edge)

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/thermalis-observatory.git
cd thermalis-observatory
```

### 2. Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Dev Server
```bash
uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to:
- **Application Interface:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs:** [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
- **ReDoc Technical Specification:** [http://127.0.0.1:8000/api/redoc](http://127.0.0.1:8000/api/redoc)

---

## Production Deployment (Vercel)

The repository is pre-configured for automated, zero-configuration deployment on **Vercel** with zero cost:

1. Push your code to GitHub, GitLab, or Bitbucket.
2. In the [Vercel Dashboard](https://vercel.com), click **Add New Project**.
3. Select your repository.
4. Leave all build settings at their defaults (`vercel.json` automatically configures function bundling and static routing).
5. Click **Deploy**.

> **Note on Edge Resilience:** The application is built with a dual-tier data access strategy. Static GeoJSON boundaries and pre-compiled JSON catalogs are located in `public/data/` and served directly by Vercel's global CDN. Even during cold starts or transient serverless outages, the map, choropleth filters, and time sliders continue to render seamlessly on the client.

---

## REST API Reference

All backend endpoints are prefixed with `/api/v1`.

### System Health
```http
GET /api/v1/health
```
Returns system uptime, active catalog version, and territorial entity counts.

### Territorial Catalog
```http
GET /api/v1/cities
```
Returns complete list of 58 territorial scopes (National, 20 Metros, 37 States) with centers, default zoom levels, and feature counts.

### Zone Metrics
```http
GET /api/v1/zones?city={slug}&year={year}&limit={limit}
```
**Parameters:**
- `city` *(string, default: "india")*: Territory slug (e.g. `india`, `chennai`, `bengaluru`, `tamil_nadu`, `maharashtra`).
- `year` *(integer, 2016–2024)*: Observation year.
- `limit` *(integer, 1–600)*: Max records returned.

### Single Feature Profile
```http
GET /api/v1/zones/{zone_id}?city={slug}
```
Returns 9-year longitudinal panel, Mann-Kendall trend significance ($p$-value and Sen's slope), and changepoints for a specific ward or district.

### Dynamic Choropleth GeoJSON
```http
GET /api/v1/zones/geojson?city={slug}&year={year}&indicator={lst|ndvi|ndbi|rainfall}
```
Returns an RFC 7946 GeoJSON FeatureCollection with pre-computed choropleth fill colors, metric values, and bounding metadata.

### OLS Multivariable Regression
```http
GET /api/v1/analytics/regression?city={slug}
```
Returns ordinary least squares (OLS) regression coefficients evaluating the relative contribution of built-up expansion (NDBI) vs vegetative cooling (NDVI) on Land Surface Temperature:
$$\text{LST} = \beta_0 + \beta_1 \cdot \text{NDBI} + \beta_2 \cdot \text{NDVI} + \epsilon$$

---

## Data Attribution & Citations

- **Boundary Data:** Administrative boundaries for India States, Union Territories, Districts, and Metropolitan Wards adapted from the open spatial repository [datta07/INDIAN-SHAPEFILES](https://github.com/datta07/INDIAN-SHAPEFILES).
- **Satellite Remote Sensing:**
  - Landsat-8/9 Collection 2 Level-2 Surface Temperature courtesy of the **U.S. Geological Survey (USGS)** and **NASA**.
  - Copernicus Sentinel-2 MSI Level-2A Surface Reflectance courtesy of the **European Space Agency (ESA)** and European Commission.
- **Precipitation Data:** Climate Hazards Group InfraRed Precipitation with Station data (CHIRPS) and India Meteorological Department (IMD) gridded reanalysis.

---

## License

This project is licensed under the **MIT License** — see the `LICENSE` file for details. Open for academic, governmental, and commercial use with attribution.
