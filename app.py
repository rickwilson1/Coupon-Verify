# Rick Wilson 9/18/25, development of ArcGIS URL call - development for Agromin Coupon Code Validation

import streamlit as st
import requests
import json
from pathlib import Path

# --- Config ---
# ArcGIS geocoding endpoint for converting address -> coordinates
GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
# File containing city/county ArcGIS endpoint URLs
ENDPOINTS_FILE = Path("endpoints.json")

# --- Load endpoints ---
if ENDPOINTS_FILE.exists():
    # Load city/county boundary services from JSON
    endpoints = json.loads(ENDPOINTS_FILE.read_text())
else:
     # If no endpoints.json found, stop with an error
    endpoints = {}
    st.error("No endpoints.json found!")

# ---- Streamlit UI ----
st.title("Coupon Eligibility Address Validator")
st.caption("Enter a California address to check if it qualifies for coupon use based on official city and county boundaries.")

# Address input
address = st.text_input("Address:")

if st.button("Lookup") and address:
    # Step 1: Convert address to latitude/longitude
    geo_params = {"SingleLine": address, "f": "json", "outFields": "*", "maxLocations": 1}
    try:
        geo_resp = requests.get(GEOCODE_URL, params=geo_params, timeout=10).json()
    except Exception as e:
        st.error(f"Error contacting geocode service: {e}")
        st.stop()

    if not geo_resp.get("candidates"):
        # No geocode match
        st.error("❌ Address not found.")
    else:
        # Extract coordinates of first match
        candidate = geo_resp["candidates"][0]
        x, y = candidate["location"]["x"], candidate["location"]["y"]

        st.success("✅ Address found!")
        st.write(f"**Matched Address:** {candidate['address']}")
        st.write(f"**Coordinates:** {y}, {x}")
        
        # Step 2: Check if coordinates fall inside any county/city boundary
        found_county = None
        found_city = None
        
        for county_name, cfg in endpoints.items():
            # Query ArcGIS REST API for county boundary match
            county_params = {
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json"
            }
            try:
                county_resp = requests.get(cfg["county_url"], params=county_params, timeout=10).json()
            except Exception as e:
                st.error(f"Error contacting county service: {e}")
                continue

            if county_resp.get("features"):
                found_county = county_name

                # Step 3: Check city layer
                try:
                    city_resp = requests.get(cfg["city_url"], params=county_params, timeout=10).json()
                except Exception as e:
                    st.error(f"Error contacting city service: {e}")
                    continue

                if city_resp.get("features"):
                    city_attr = city_resp["features"][0]["attributes"]
                    found_city = city_attr.get("CITY_NAME", "Unknown")
                else:
                    found_city = f"Unincorporated {county_name}"
                break

        # Step 4: Display final results
        st.write(f"**County:** {found_county or 'Not found'}")
        st.write(f"**City:** {found_city or 'Not found'}")
