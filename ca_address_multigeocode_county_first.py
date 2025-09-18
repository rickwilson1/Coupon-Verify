import streamlit as st
import requests
import json
from pathlib import Path

# --- Config ---
GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

# Load endpoints from JSON
with open(Path(__file__).parent / "endpoints.json") as f:
    ENDPOINTS = json.load(f)

st.set_page_config(page_title="Coupon Eligibility Address Validator", layout="centered")
st.title("🧾 Coupon Eligibility Address Validator")
st.write("Enter a California address to check if it qualifies for coupon use "
         "based on **official city and county boundaries.**")

address = st.text_input("Address:")

if st.button("Lookup") and address:
    # Step 1: Geocode
    params = {"SingleLine": address, "f": "json", "outFields": "*", "maxLocations": 1}
    geo_resp = requests.get(GEOCODE_URL, params=params).json()

    if not geo_resp.get("candidates"):
        st.error("Address not found.")
    else:
        candidate = geo_resp["candidates"][0]
        x, y = candidate["location"]["x"], candidate["location"]["y"]

        st.success("✅ Address found!")
        st.write(f"**Matched Address:** {candidate['address']}")

        # Loop over counties in JSON
        for county_name, urls in ENDPOINTS.items():
            st.subheader(f"🔍 Checking {county_name}")

            # County check
            county_params = {
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json"
            }
            county_resp = requests.get(urls["county_url"], params=county_params).json()
            county_result = None
            if county_resp.get("features"):
                county_result = county_resp["features"][0]["attributes"]

            # City check
            city_resp = requests.get(urls["city_url"], params=county_params).json()
            city_result = None
            if city_resp.get("features"):
                city_result = city_resp["features"][0]["attributes"]

            # Display
            st.write(f"**County:** {county_result.get('BOUNDARY') if county_result else 'Not found'}")
            st.write(f"**City:** {city_result.get('CITY_NAME') if city_result else 'Not found'}")

        with st.expander("Debug Info"):
            st.json({"GeocodeResponse": candidate})
