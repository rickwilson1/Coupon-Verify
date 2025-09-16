import streamlit as st
import requests
import json

# ---------------- GOOGLE API KEY ----------------
GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]

# ---------------- LOAD CONFIG ----------------
with open("ca_city_endpoints_final.json") as f:
    config = json.load(f)

CITY_ENDPOINTS = config["CITY_ENDPOINTS"]
COUNTY_ENDPOINTS = config["COUNTY_ENDPOINTS"]

# ---------------- UTILS ----------------
def geocode_address(address, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            result = data['results'][0]
            location = result['geometry']['location']
            lat, lng = location['lat'], location['lng']

            # Extract ZIP code if available
            zip_code = None
            for comp in result['address_components']:
                if 'postal_code' in comp['types']:
                    zip_code = comp['long_name']

            return lat, lng, zip_code
    return None, None, None

def query_arcgis(endpoint, lat, lon):
    if not endpoint or not endpoint.startswith("http"):
        return False  # Skip invalid or blank URLs

    url = f"{endpoint}/query"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "returnCountOnly": "false",
        "returnGeometry": "false",
        "outFields": "*",
        "f": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "features" in data and len(data["features"]) > 0:
                return True
    except Exception as e:
        st.warning(f"ArcGIS query failed for {endpoint}: {e}")
    return False

# ---------------- STREAMLIT APP ----------------
st.title("California Address Lookup")

address = st.text_input("Enter an address in California to get coordinates, ZIP, county, and official city boundary check.")

if st.button("Lookup"):
    lat, lon, zip_code = geocode_address(address, GOOGLE_KEY)

    if not lat or not lon:
        st.error("Geocoding failed: could not find location.")
    else:
        st.success("Address found!")
        st.write("**Coordinates:**", lat, ",", lon)
        st.write("**ZIP Code:**", zip_code if zip_code else "Not Available")

        # ---------------- COUNTY LOOKUP ----------------
        county_name = "Authoritative Boundary Not Available"
        for county_key, county_entry in COUNTY_ENDPOINTS.items():
            county_url = county_entry.get("url", "")
            if query_arcgis(county_url, lat, lon):
                county_name = county_key
                break
        st.write("**County:**", county_name)

        # ---------------- CITY LOOKUP ----------------
        city_name = "Authoritative Boundary Not Available"
        for city_key, city_entry in CITY_ENDPOINTS.items():
            city_url = city_entry.get("url", "")
            if query_arcgis(city_url, lat, lon):
                city_name = city_key
                break
        st.write("**City:**", city_name)
