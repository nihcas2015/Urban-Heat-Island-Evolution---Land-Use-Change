"""
backend/cities.py
-----------------
Configuration for each supported city.
  geojson_url     -> GitHub raw URL for district-level GeoJSON
  district_filter -> list of district names to filter from state GeoJSON
  districts       -> canonical list of district/zone names
  baseline        -> UHI parameters calibrated from published literature
"""

CITIES = {
    "chennai": {
        "name": "Chennai",
        "state": "Tamil Nadu",
        "center": [13.08, 80.27],
        "zoom": 11,
        "use_local_wards": True,   # 200 actual municipal wards from GEE
        "geojson_url": None,
        "district_filter": None,
        "districts": [str(i) for i in range(1, 201)],
        "baseline": { "lst": 39.4, "ndvi": 0.18, "ndbi": 0.06, "rainfall": 1400 },
    },
    "delhi": {
        "name": "Delhi",
        "state": "Delhi NCR",
        "center": [28.65, 77.23],
        "zoom": 10,
        "use_local_wards": False,
        "geojson_url": "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES/DELHI/DELHI_DISTRICTS.geojson",
        "district_filter": None,
        "districts": [
            "Central", "East", "New Delhi", "North", "North East",
            "North West", "Shahdara", "South", "South East", "South West", "West"
        ],
        "baseline": { "lst": 41.8, "ndvi": 0.11, "ndbi": 0.13, "rainfall": 780,
                      "lst_spread": 4.8, "warming_rate": 0.14, "seed": 101 },
    },
    "mumbai": {
        "name": "Mumbai",
        "state": "Maharashtra",
        "center": [19.07, 72.88],
        "zoom": 10,
        "use_local_wards": False,
        "geojson_url": "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES/MAHARASHTRA/MAHARASHTRA_DISTRICTS.geojson",
        "district_filter": ["Mumbai", "Mumbai Suburban", "Thane", "Palghar"],
        "districts": ["Mumbai", "Mumbai Suburban", "Thane", "Palghar"],
        "baseline": { "lst": 35.6, "ndvi": 0.19, "ndbi": 0.09, "rainfall": 2400,
                      "lst_spread": 3.6, "warming_rate": 0.08, "seed": 202 },
    },
    "bengaluru": {
        "name": "Bengaluru",
        "state": "Karnataka",
        "center": [12.97, 77.59],
        "zoom": 10,
        "use_local_wards": False,
        "geojson_url": "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES/KARNATAKA/KARNATAKA_DISTRICTS.geojson",
        "district_filter": ["Bangalore", "Bengaluru Rural", "Ramanagara", "Tumakuru", "Chikkaballapura"],
        "districts": ["Bangalore", "Bengaluru Rural", "Ramanagara", "Tumakuru", "Chikkaballapura"],
        "baseline": { "lst": 34.2, "ndvi": 0.22, "ndbi": 0.08, "rainfall": 970,
                      "lst_spread": 4.2, "warming_rate": 0.16, "seed": 303 },
    },
    "hyderabad": {
        "name": "Hyderabad",
        "state": "Telangana",
        "center": [17.38, 78.48],
        "zoom": 10,
        "use_local_wards": False,
        "geojson_url": "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES/TELANGANA/TELANGANA_DISTRICTS.geojson",
        "district_filter": ["Hyderabad", "Medchal Malkajgiri", "Sangareddy", "Yadadri Bhuvanagiri"],
        "districts": ["Hyderabad", "Medchal Malkajgiri", "Sangareddy", "Yadadri Bhuvanagiri"],
        "baseline": { "lst": 39.7, "ndvi": 0.14, "ndbi": 0.11, "rainfall": 820,
                      "lst_spread": 4.5, "warming_rate": 0.13, "seed": 404 },
    },
    "kolkata": {
        "name": "Kolkata",
        "state": "West Bengal",
        "center": [22.57, 88.36],
        "zoom": 10,
        "use_local_wards": False,
        "geojson_url": "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES/WEST%20BENGAL/WEST%20BENGAL_DISTRICTS.geojson",
        "district_filter": ["Kolkata", "Howrah", "Hooghly"],
        "districts": ["Kolkata", "Howrah", "Hooghly"],
        "baseline": { "lst": 37.8, "ndvi": 0.20, "ndbi": 0.09, "rainfall": 1750,
                      "lst_spread": 3.9, "warming_rate": 0.10, "seed": 505 },
    },
}

YEARS = list(range(2016, 2025))
