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

st.write("Loaded cities:", list(CITY_ENDPOINTS.keys()))
st.write("Loaded counties:", list(COUNTY_ENDPOINTS.keys()))

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


def query_arcgis(entry, lat, lon):
    """Query an ArcGIS REST endpoint and return True if a boundary match is found."""
    if not entry:
        return False

    # Handle both string and dict entries
    url = entry.get("url") if isinstance(entry, dict) else entry
    where_clause = entry.get("filter", "1=1") if isinstance(entry, dict) else "1=1"

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

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "features" in data and data["features"]:
            return True
    except Exception as e:
        st.warning(f"ArcGIS query failed for {url}: {e}")
    return False


# ---------------- STREAMLIT APP ----------------
st.markdown(
    """
    <div style="text-align: center; padding: 20px; background-color: var(--card-bg); border-radius: 10px;">
        <h1 style="color: var(--title-color);">Coupon Eligibility Address Validator</h1>
        <p style="font-size:18px; color: var(--text-color);">
            Enter a California address to check if it qualifies for coupon use 
            based on <b>official city and county boundaries</b>.
        </p>
    </div>

    <style>
        /* Light mode */
        @media (prefers-color-scheme: light) {
            :root {
                --card-bg: #f0f2f6;       /* light gray background */
                --title-color: #2E86C1;   /* blue */
                --text-color: #000000;    /* black */
            }
        }
        /* Dark mode */
        @media (prefers-color-scheme: dark) {
            :root {
                --card-bg: #2b2b2b;       /* darker gray for card */
                --title-color: #4DA3FF;   /* lighter blue for contrast */
                --text-color: #FFFFFF;    /* white */
            }
        }
    </style>
    """,
    unsafe_allow_html=True
)

address = st.text_input("Address:")

if st.button("Lookup"):
    lat, lon, zip_code = geocode_address(address, GOOGLE_KEY)

    if not lat or not lon:
        st.error("Geocoding failed: could not find location.")
    else:
        st.success("Address found!")
        st.write("**Coordinates:**", lat, ",", lon)
        st.write("**ZIP Code:**", zip_code if zip_code else "Not Available")

        # ---------------- COUNTY LOOKUP ----------------
        county_name = None
        for county_key, county_entry in COUNTY_ENDPOINTS.items():
            county_url = county_entry if isinstance(county_entry, str) else county_entry.get("url", "")
            if query_arcgis(county_entry, lat, lon):
                county_name = county_key
                break
        if not county_name:
            county_name = "Authoritative Boundary Not Available"
        st.write("**County:**", county_name)

        # ---------------- CITY LOOKUP ----------------
        city_name = None
        for city_key, city_entry in CITY_ENDPOINTS.items():
            if query_arcgis(city_entry, lat, lon):
                city_name = city_key
                break

        # Accept city result if in county OR city endpoint
        if county_name != "Authoritative Boundary Not Available":
            city_result = f"Valid (within {county_name})"
        elif city_name:
            city_result = city_name
        else:
            city_result = "Authoritative Boundary Not Available"

        st.write("**City:**", city_result)
