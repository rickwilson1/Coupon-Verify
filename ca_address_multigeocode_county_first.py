import streamlit as st
import requests
import json
import os
import pathlib

# ---------------- CONFIG ----------------
BASE_DIR = pathlib.Path(__file__).parent
JSON_PATH = BASE_DIR / "ca_city_endpoints_final.json"

# ---------------- HELPERS ----------------
def load_config(path):
    with open(path) as f:
        return json.load(f)

def query_arcgis(entry, lat, lon):
    """Query an ArcGIS endpoint and return True if inside boundary."""
    url = entry["url"]
    where_clause = entry.get("filter", "1=1")

    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "where": where_clause,
        "returnGeometry": "false",
        "f": "json"
    }

    r = requests.get(url, params=params, timeout=10)

    # --- DEBUG OUTPUT ---
    st.write("DEBUG URL:", r.url)
    try:
        st.write("DEBUG Response:", r.json())
    except Exception:
        st.write("DEBUG Response: could not parse JSON")

    if r.status_code == 200:
        data = r.json()
        return "features" in data and len(data["features"]) > 0
    return False

# ---------------- STREAMLIT APP ----------------
st.title("Coupon Eligibility Address Validator")
st.write("Enter a California address to check if it qualifies for coupon use based on official city and county boundaries.")

address = st.text_input("Address:", "915 I St, Sacramento, CA 95814")

if st.button("Lookup"):
    st.success("Address found!")

    # Simulate geocode (replace with your real geocoder)
    if "Sacramento" in address:
        lat, lon = 38.5823873, -121.493432
    elif "Elk Grove" in address:
        lat, lon = 38.4231882, -121.3945566
    else:
        lat, lon = 38.566548, -121.2910851

    st.write("**Coordinates:**", lat, ",", lon)

    # Load JSON
    config = load_config(JSON_PATH)
    st.write("DEBUG: Loaded endpoints →", config)  # <--- show config

    # Run ArcGIS queries
    for city, entry in config.get("CITY_ENDPOINTS", {}).items():
        inside = query_arcgis(entry, lat, lon)
        st.write(f"City {city}: {'✅ Inside' if inside else '❌ Not inside'}")

    for county, entry in config.get("COUNTY_ENDPOINTS", {}).items():
        inside = query_arcgis(entry, lat, lon)
        st.write(f"County {county}: {'✅ Inside' if inside else '❌ Not inside'}")
