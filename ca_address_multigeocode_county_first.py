import streamlit as st
import requests
import json
from pathlib import Path

# --- Config ---
GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
ENDPOINTS_FILE = Path("endpoints.json")

# --- Load endpoints ---
if ENDPOINTS_FILE.exists():
    endpoints = json.loads(ENDPOINTS_FILE.read_text())
else:
    endpoints = {}
    st.error("No endpoints.json found!")

st.title("Coupon Eligibility Address Validator")
st.caption("Enter a California address to check if it qualifies for coupon use based on official city and county boundaries.")

address = st.text_input("Address:", "915 I St, Sacramento, CA 95814")

if st.button("Lookup") and address:
    # Step 1: Geocode
    geo_params = {"SingleLine": address, "f": "json", "outFields": "*", "maxLocations": 1}
    geo_resp = requests.get(GEOCODE_URL, params=geo_params).json()

    if not geo_resp.get("candidates"):
        st.error("❌ Address not found.")
    else:
        candidate = geo_resp["candidates"][0]
        x, y = candidate["location"]["x"], candidate["location"]["y"]

        st.success("✅ Address found!")
        st.write(f"**Matched Address:** {candidate['address']}")
        st.write(f"**Coordinates:** {y}, {x}")

        # Step 2: Loop through counties
        found_county = None
        found_city = None

        for county_name, cfg in endpoints.items():
            county_params = {
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json"
            }
            county_resp = requests.get(cfg["county_url"], params=county_params).json()

            if county_resp.get("features"):
                found_county = county_name

                # Step 3: Check city layer
                city_resp = requests.get(cfg["city_url"], params=county_params).json()
                if city_resp.get("features"):
                    city_attr = city_resp["features"][0]["attributes"]
                    found_city = city_attr.get("CITY_NAME", "Unknown")
                else:
                    found_city = f"Unincorporated {county_name}"
                break

        # Step 4: Display
        st.write(f"**County:** {found_county or 'Not found'}")
        st.write(f"**City:** {found_city or 'Not found'}")

        with st.expander("Debug Info"):
            st.json({"Candidate": candidate, "Endpoints": endpoints})
