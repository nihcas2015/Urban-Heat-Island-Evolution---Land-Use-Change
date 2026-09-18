# Urban Heat Island Evolution & Land-Use Change — Chennai

> An interactive spatial dashboard tracking land surface temperature, vegetation loss, and urban expansion across **200 Chennai wards from 2016 to 2024**, using Sentinel-2 and Landsat-8/9 satellite imagery processed through Google Earth Engine.

---

## Why This Exists

Chennai has experienced rapid urbanisation over the past decade — replacing vegetation and open land with built-up surfaces that absorb and retain heat. The Urban Heat Island (UHI) effect is a direct consequence: city centres are measurably hotter than surrounding rural areas, intensifying heat stress for residents, straining energy systems, and compounding climate vulnerability.

Most UHI studies present static snapshots. This project takes a **sequential, ward-level approach** — detecting not just where the city is hot, but *when* temperatures shifted, *which wards* are warming fastest, and *what land-use indicators* drive that warming. The results are surfaced through an interactive web dashboard, making the data accessible beyond an academic PDF.

---

## What It Shows

| Layer | What you can see |
|---|---|
| **Heat Risk Map** | Choropleth of LST, NDVI, or NDBI for any year 2016–2024 across all 200 wards |
| **Ward Inspector** | Click any ward: full 9-year LST + NDVI trend chart, trend classification, change-point years |
| **City Trends** | City-wide average LST/NDVI/NDBI over time — how the whole city has evolved |
| **Zone Comparison** | Average LST per administrative zone (Tiruvottiyur, Manali, etc.) |
| **Rankings** | Top 15 hottest, most vegetated, or most built-up wards for 2024 |
| **Regression Card** | OLS model summary: how NDVI, NDBI, and rainfall together explain LST variability |
| **LST Distribution** | Histogram of how LST is distributed across wards in 2024 |

---

## Data & Methods

**Satellite sources**
- Sentinel-2 Surface Reflectance (2016–2024) — NDVI and NDBI via band math
- Landsat-8/9 Collection 2 — Land Surface Temperature via thermal band
- All processed in Google Earth Engine; annual median composites per ward

**Ward boundaries**
- 200 actual Chennai Corporation ward polygons (GeoJSON)
- Mean values per ward extracted with `reduceRegions`

**Sequential mining methods**
- **Mann-Kendall test** (pymannkendall) — non-parametric monotonic trend detection per ward LST series
- **PELT change-point detection** (ruptures) — identifies structural breaks (sudden LST shifts) within ward time series
- **OLS Regression** (scikit-learn) — LST ~ NDVI + NDBI + rainfall, pooled across all ward-years

**Key findings**
- NDBI has a stronger positive effect on LST (β = 23.5) than NDVI has a cooling effect (β = 5.7)
- R² = 0.17 at ward scale — expected, since ward-mean averaging smooths sub-ward micro-climate variation
- 2015 excluded: Sentinel-2 coverage over India was sparse before mid-2016

---

## Repository Structure

```
uhi-dashboard/
├── index.html          # Single-page dashboard
├── style.css           # Dark satellite-themed stylesheet
├── app.js              # All interactivity — linear flow, no build step
└── data/
    ├── wards_2024.geojson        # 200 ward polygons + 2024 indicator values
    ├── ward_timeseries_full.csv  # LST, NDVI, NDBI, rainfall per ward per year
    ├── trend_significance.csv    # Mann-Kendall result per ward
    ├── changepoints.csv          # PELT change-point years per ward
    └── regression_summary.json   # OLS coefficients and R²
```

No build tools, no bundler, no server needed. The dashboard runs entirely in the browser from static files.

---

## Deploying to Vercel

1. Push this repository to GitHub
2. Import the repository in [vercel.com](https://vercel.com)
3. Set the **Root Directory** to `uhi-dashboard`
4. Deploy — Vercel will serve it as a static site

---

## Limitations & Future Scope

- **Short series** — 9 years is near the minimum for robust trend detection; extending to 2030+ will improve Mann-Kendall sensitivity
- **Ward-mean averaging** — smooths sub-ward hotspots (e.g. industrial clusters within a ward)
- **No causal inference** — regression identifies association, not causality between land use and temperature
- Future work could add monthly resolution, multi-city comparison, and Prophet-based LST forecasting at the ward level

---

*Data processed in Google Colab · Dashboard built with Leaflet.js and Chart.js · No external backend*

