import streamlit as st
import requests
import json

# --- Load JSON config ---
with open("ca_city_endpoints_final.json") as f:
    config = json.load(f)

CITY_ENDPOINTS = config["CITY_ENDPOINTS"]
COUNTY_ENDPOINTS = config["COUNTY_ENDPOINTS"]

# --- Google Geocoding (replace with your API key in Streamlit secrets) ---
GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]

def geocode_address(address, api_key):
    """Return (lat, lon, zip) for an address using Google Maps API."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        if data["status"] == "OK":
            result = data["results"][0]
            loc = result["geometry"]["location"]
            lat, lon = loc["lat"], loc["lng"]

            zip_code = None
            for comp in result["address_components"]:
                if "postal_code" in comp["types"]:
                    zip_code = comp["long_name"]
            return lat, lon, zip_code
    return None, None, None


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
    if r.status_code == 200:
        data = r.json()
        return "features" in data and len(data["features"]) > 0
    return False


# --- Streamlit UI ---
st.title("Coupon Eligibility Address Validator")

address = st.text_input("Enter address in Sacramento County:")

if st.button("Lookup"):
    lat, lon, zip_code = geocode_address(address, GOOGLE_KEY)

    if not lat or not lon:
        st.error("Geocoding failed: could not find location.")
    else:
        st.success("Address found!")
        st.write("**Coordinates:**", lat, ",", lon)
        st.write("**ZIP Code:**", zip_code if zip_code else "Not Available")

        # --- County Check ---
        county_name = "Authoritative Boundary Not Available"
        for county_key, county_entry in COUNTY_ENDPOINTS.items():
            if query_arcgis(county_entry, lat, lon):
                county_name = county_key
                break
        st.write("**County:**", county_name)

        # --- City Check ---
        city_name = "Authoritative Boundary Not Available"
        for city_key, city_entry in CITY_ENDPOINTS.items():
            if query_arcgis(city_entry, lat, lon):
                city_name = city_key
                break
        st.write("**City:**", city_name)
