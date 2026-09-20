"""
backend/cities.py
-----------------
Territorial catalog for National (All India), Metropolitan Cities (20 Cities with Municipal Wards),
and State-Level (37 States & UTs with Administrative Districts).
All boundary data is embedded locally in data/geojson/.
"""

# All 37 States & Union Territories of India
INDIA_STATES = [
    "ANDAMAN & NICOBAR", "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM",
    "BIHAR", "CHANDIGARH", "CHHATTISGARH", "DADRA & NAGAR HAVELI",
    "DAMAN & DIU", "DELHI", "GOA", "GUJARAT", "HARYANA",
    "HIMACHAL PRADESH", "JAMMU & KASHMIR", "JHARKHAND", "KARNATAKA",
    "KERALA", "LADAKH", "LAKSHADWEEP", "MADHYA PRADESH", "MAHARASHTRA",
    "MANIPUR", "MEGHALAYA", "MIZORAM", "NAGALAND", "ODISHA",
    "PUDUCHERRY", "PUNJAB", "RAJASTHAN", "SIKKIM", "TAMIL NADU",
    "TELANGANA", "TRIPURA", "UTTAR PRADESH", "UTTARAKHAND", "WEST BENGAL"
]

# Top 20 Indian Metropolitan Cities with actual municipal ward GeoJSONs embedded
METRO_CITIES = {
    "bengaluru":        {"name": "Bengaluru",        "state": "Karnataka",      "center": [12.9716, 77.5946], "zoom": 11, "type": "BBMP Municipal Wards"},
    "delhi":            {"name": "Delhi NCR",        "state": "Delhi",          "center": [28.6139, 77.2090], "zoom": 10, "type": "MCD Municipal Wards"},
    "mumbai":           {"name": "Mumbai",           "state": "Maharashtra",    "center": [19.0760, 72.8777], "zoom": 11, "type": "BMC Administrative Wards"},
    "hyderabad":        {"name": "Hyderabad",        "state": "Telangana",      "center": [17.3850, 78.4867], "zoom": 11, "type": "GHMC Municipal Wards"},
    "chennai":          {"name": "Chennai",          "state": "Tamil Nadu",     "center": [13.0827, 80.2707], "zoom": 11, "type": "GCC Municipal Wards"},
    "ahmadabad":        {"name": "Ahmedabad",        "state": "Gujarat",        "center": [23.0225, 72.5714], "zoom": 11, "type": "AMC Municipal Wards"},
    "pune":             {"name": "Pune",             "state": "Maharashtra",    "center": [18.5204, 73.8567], "zoom": 11, "type": "PMC Municipal Wards"},
    "jaipur":           {"name": "Jaipur",           "state": "Rajasthan",      "center": [26.9124, 75.7873], "zoom": 11, "type": "JMC Municipal Wards"},
    "surat":            {"name": "Surat",            "state": "Gujarat",        "center": [21.1702, 72.8311], "zoom": 11, "type": "SMC Municipal Wards"},
    "lucknow":          {"name": "Lucknow",          "state": "Uttar Pradesh",  "center": [26.8467, 80.9462], "zoom": 11, "type": "LMC Municipal Wards"},
    "kanpur":           {"name": "Kanpur",           "state": "Uttar Pradesh",  "center": [26.4499, 80.3319], "zoom": 11, "type": "KMC Municipal Wards"},
    "bhopal":           {"name": "Bhopal",           "state": "Madhya Pradesh", "center": [23.2599, 77.4126], "zoom": 11, "type": "BMC Municipal Wards"},
    "indore":           {"name": "Indore",           "state": "Madhya Pradesh", "center": [22.7196, 75.8577], "zoom": 11, "type": "IMC Municipal Wards"},
    "nagpur":           {"name": "Nagpur",           "state": "Maharashtra",    "center": [21.1458, 79.0882], "zoom": 11, "type": "NMC Municipal Wards"},
    "patna":            {"name": "Patna",            "state": "Bihar",          "center": [25.5941, 85.1376], "zoom": 11, "type": "PMC Municipal Wards"},
    "visakhapatnam":    {"name": "Visakhapatnam",    "state": "Andhra Pradesh", "center": [17.6868, 83.2185], "zoom": 11, "type": "GVMC Municipal Wards"},
    "vadodara":         {"name": "Vadodara",         "state": "Gujarat",        "center": [22.3072, 73.1812], "zoom": 11, "type": "VMC Municipal Wards"},
    "thane":            {"name": "Thane",            "state": "Maharashtra",    "center": [19.2183, 72.9781], "zoom": 11, "type": "TMC Municipal Wards"},
    "navi_mumbai":      {"name": "Navi Mumbai",      "state": "Maharashtra",    "center": [19.0330, 73.0297], "zoom": 11, "type": "NMMC Municipal Wards"},
    "pimpri_chinchwad": {"name": "Pimpri Chinchwad", "state": "Maharashtra",    "center": [18.6298, 73.7997], "zoom": 11, "type": "PCMC Municipal Wards"},
}

# Regional climate baselines for all 37 Indian States
STATE_CLIMATES = {
    "RAJASTHAN": {"lst": 43.4, "ndvi": 0.09, "ndbi": 0.14, "rain": 450, "spread": 4.6},
    "GUJARAT": {"lst": 42.1, "ndvi": 0.12, "ndbi": 0.12, "rain": 750, "spread": 4.2},
    "HARYANA": {"lst": 41.8, "ndvi": 0.14, "ndbi": 0.11, "rain": 620, "spread": 3.8},
    "PUNJAB": {"lst": 40.9, "ndvi": 0.18, "ndbi": 0.10, "rain": 680, "spread": 3.5},
    "DELHI": {"lst": 42.6, "ndvi": 0.11, "ndbi": 0.15, "rain": 780, "spread": 4.8},
    "UTTAR PRADESH": {"lst": 41.2, "ndvi": 0.17, "ndbi": 0.11, "rain": 920, "spread": 4.5},
    "MADHYA PRADESH": {"lst": 41.6, "ndvi": 0.16, "ndbi": 0.10, "rain": 1050, "spread": 4.4},
    "BIHAR": {"lst": 40.5, "ndvi": 0.19, "ndbi": 0.09, "rain": 1150, "spread": 3.9},
    "JHARKHAND": {"lst": 39.8, "ndvi": 0.22, "ndbi": 0.08, "rain": 1300, "spread": 3.7},
    "CHHATTISGARH": {"lst": 40.2, "ndvi": 0.24, "ndbi": 0.08, "rain": 1350, "spread": 3.6},
    "ODISHA": {"lst": 39.5, "ndvi": 0.23, "ndbi": 0.08, "rain": 1450, "spread": 3.8},
    "MAHARASHTRA": {"lst": 38.8, "ndvi": 0.18, "ndbi": 0.10, "rain": 1200, "spread": 4.5},
    "TELANGANA": {"lst": 40.3, "ndvi": 0.15, "ndbi": 0.11, "rain": 850, "spread": 4.1},
    "ANDHRA PRADESH": {"lst": 39.7, "ndvi": 0.17, "ndbi": 0.09, "rain": 950, "spread": 4.0},
    "KARNATAKA": {"lst": 36.8, "ndvi": 0.22, "ndbi": 0.09, "rain": 1150, "spread": 4.2},
    "TAMIL NADU": {"lst": 38.9, "ndvi": 0.18, "ndbi": 0.08, "rain": 1100, "spread": 4.3},
    "KERALA": {"lst": 33.4, "ndvi": 0.32, "ndbi": 0.05, "rain": 2800, "spread": 3.2},
    "GOA": {"lst": 34.2, "ndvi": 0.30, "ndbi": 0.06, "rain": 2600, "spread": 2.8},
    "WEST BENGAL": {"lst": 38.6, "ndvi": 0.21, "ndbi": 0.09, "rain": 1700, "spread": 3.9},
    "ASSAM": {"lst": 32.8, "ndvi": 0.29, "ndbi": 0.06, "rain": 2200, "spread": 3.4},
    "MEGHALAYA": {"lst": 27.5, "ndvi": 0.34, "ndbi": 0.04, "rain": 3400, "spread": 3.0},
    "ARUNACHAL PRADESH": {"lst": 24.2, "ndvi": 0.38, "ndbi": 0.03, "rain": 2800, "spread": 3.5},
    "MANIPUR": {"lst": 28.1, "ndvi": 0.31, "ndbi": 0.05, "rain": 1800, "spread": 3.0},
    "MIZORAM": {"lst": 27.4, "ndvi": 0.35, "ndbi": 0.04, "rain": 2100, "spread": 2.9},
    "NAGALAND": {"lst": 26.8, "ndvi": 0.34, "ndbi": 0.04, "rain": 1900, "spread": 3.1},
    "TRIPURA": {"lst": 33.1, "ndvi": 0.28, "ndbi": 0.06, "rain": 2100, "spread": 3.2},
    "SIKKIM": {"lst": 21.4, "ndvi": 0.35, "ndbi": 0.03, "rain": 2600, "spread": 3.6},
    "HIMACHAL PRADESH": {"lst": 23.6, "ndvi": 0.28, "ndbi": 0.05, "rain": 1250, "spread": 4.5},
    "UTTARAKHAND": {"lst": 26.8, "ndvi": 0.29, "ndbi": 0.06, "rain": 1550, "spread": 4.6},
    "JAMMU & KASHMIR": {"lst": 22.1, "ndvi": 0.24, "ndbi": 0.05, "rain": 1050, "spread": 4.8},
    "LADAKH": {"lst": 17.8, "ndvi": 0.06, "ndbi": 0.04, "rain": 120, "spread": 4.2},
    "CHANDIGARH": {"lst": 41.5, "ndvi": 0.16, "ndbi": 0.14, "rain": 950, "spread": 2.5},
    "PUDUCHERRY": {"lst": 38.2, "ndvi": 0.18, "ndbi": 0.09, "rain": 1300, "spread": 2.4},
    "ANDAMAN & NICOBAR": {"lst": 32.5, "ndvi": 0.36, "ndbi": 0.04, "rain": 3100, "spread": 2.6},
    "LAKSHADWEEP": {"lst": 32.2, "ndvi": 0.33, "ndbi": 0.04, "rain": 1900, "spread": 2.2},
    "DADRA & NAGAR HAVELI": {"lst": 37.4, "ndvi": 0.22, "ndbi": 0.08, "rain": 1950, "spread": 2.5},
    "DAMAN & DIU": {"lst": 36.8, "ndvi": 0.16, "ndbi": 0.10, "rain": 1600, "spread": 2.3}
}

# Geographic center and default zoom level for each state/UT
STATE_CENTERS = {
    "TAMIL NADU": ([11.12, 78.65], 7),
    "MAHARASHTRA": ([19.75, 75.71], 7),
    "KARNATAKA": ([15.31, 75.71], 7),
    "UTTAR PRADESH": ([26.84, 80.94], 7),
    "KERALA": ([10.85, 76.27], 8),
    "GUJARAT": ([22.25, 71.19], 7),
    "RAJASTHAN": ([27.02, 74.21], 7),
    "WEST BENGAL": ([22.98, 87.85], 7),
    "DELHI": ([28.65, 77.23], 10),
    "TELANGANA": ([18.11, 79.01], 7),
    "ANDHRA PRADESH": ([15.91, 79.74], 7),
    "MADHYA PRADESH": ([22.97, 78.65], 7),
    "BIHAR": ([25.09, 85.31], 7),
    "PUNJAB": ([31.14, 75.34], 8),
    "HARYANA": ([29.05, 76.08], 8),
    "ODISHA": ([20.95, 85.09], 7),
    "ASSAM": ([26.20, 92.93], 7),
    "JAMMU & KASHMIR": ([33.77, 76.57], 7),
    "JHARKHAND": ([23.61, 85.27], 7),
    "CHHATTISGARH": ([21.27, 81.86], 7),
    "HIMACHAL PRADESH": ([31.10, 77.17], 8),
    "UTTARAKHAND": ([30.06, 79.01], 8),
    "GOA": ([15.29, 74.12], 9),
    "TRIPURA": ([23.94, 91.98], 8),
    "MEGHALAYA": ([25.46, 91.36], 8),
    "MANIPUR": ([24.66, 93.90], 8),
    "NAGALAND": ([26.15, 94.56], 8),
    "ARUNACHAL PRADESH": ([28.21, 94.72], 7),
    "MIZORAM": ([23.16, 92.93], 8),
    "SIKKIM": ([27.53, 88.51], 9),
    "LADAKH": ([34.15, 77.57], 7),
    "PUDUCHERRY": ([11.94, 79.80], 9),
    "CHANDIGARH": ([30.73, 76.77], 11),
    "ANDAMAN & NICOBAR": ([11.74, 92.65], 7),
    "DADRA & NAGAR HAVELI": ([20.18, 73.01], 10),
    "DAMAN & DIU": ([20.42, 72.83], 10),
    "LAKSHADWEEP": ([10.56, 72.64], 8),
}

# Aliases
ALIASES = {
    "ahmedabad": "ahmadabad",
    "odisha": "orissa",
    "kolkata": "west_bengal",
    "bangalore": "bengaluru",
}

YEARS = list(range(2016, 2025))


def normalize_slug(s):
    """Normalize any string to canonical slug."""
    if not s:
        return "india"
    clean = s.strip().lower().replace("-", "_").replace(" ", "_")
    return ALIASES.get(clean, clean)


def get_state_from_slug(slug):
    """Resolve normalized slug back to canonical state name."""
    norm = normalize_slug(slug)
    for st in INDIA_STATES:
        if st.lower().replace("-", "_").replace(" ", "_") == norm:
            return st
    if norm == "orissa":
        return "ODISHA"
    return None


def get_scope_info(scope_key):
    """Resolve complete territorial configuration for national, metropolitan, or state scope."""
    slug = normalize_slug(scope_key)

    # 1. National
    if slug == "india":
        return {
            "key": "india",
            "name": "All India",
            "state": "National Overview",
            "center": [22.97, 78.65],
            "zoom": 5,
            "is_national": True,
            "is_metro": False,
            "use_local_wards": False,
            "baseline": {"lst": 36.5, "ndvi": 0.22, "ndbi": 0.08, "rainfall": 1250, "spread": 5.0},
        }

    # 2. Metropolitan City (Wards)
    if slug in METRO_CITIES:
        m = METRO_CITIES[slug]
        st_clim = STATE_CLIMATES.get(m["state"].upper(), {"lst": 38.0, "ndvi": 0.16, "ndbi": 0.10, "rain": 1100, "spread": 4.0})
        return {
            "key": slug,
            "name": m["name"],
            "state": m["state"],
            "center": m["center"],
            "zoom": m["zoom"],
            "is_national": False,
            "is_metro": True,
            "use_local_wards": True,
            "baseline": {
                "lst": st_clim["lst"] + 0.8,
                "ndvi": max(0.08, st_clim["ndvi"] - 0.04),
                "ndbi": st_clim["ndbi"] + 0.04,
                "rainfall": st_clim["rain"],
                "spread": st_clim.get("spread", 4.0),
            },
        }

    # 3. State Scope (Districts)
    st_name = get_state_from_slug(slug)
    if not st_name:
        return get_scope_info("india")

    center, zoom = STATE_CENTERS.get(st_name, ([22.0, 78.0], 7))
    clim = STATE_CLIMATES.get(st_name, {"lst": 37.0, "ndvi": 0.20, "ndbi": 0.08, "rain": 1200, "spread": 4.0})

    return {
        "key": slug,
        "name": st_name.title(),
        "state": st_name.title(),
        "center": center,
        "zoom": zoom,
        "is_national": False,
        "is_metro": False,
        "use_local_wards": False,
        "baseline": {
            "lst": clim["lst"],
            "ndvi": clim["ndvi"],
            "ndbi": clim["ndbi"],
            "rainfall": clim["rain"],
            "spread": clim.get("spread", 4.0),
        },
    }
