import streamlit as st
import requests
import json

# ---------------- GOOGLE API KEY ----------------
GOOGLE_KEY = "AIzaSyBLbTDyCwHIbA9tr9hgxL2C5x8Nn0dt6_4"

# ---------------- LOAD CONFIG ----------------
with open("ca_city_endpoints_final.json") as f:
    config = json.load(f)

CITY_ENDPOINTS = config["CITY_ENDPOINTS"]
COUNTY_ENDPOINTS = config["COUNTY_ENDPOINTS"]

# ---------------- GEOCODING ----------------
def geocode_address(address, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}
    r = requests.get(url, params=params).json()

    if r["status"] != "OK":
        return None, None, None, None, None, None, r["status"]

    result = r["results"][0]
    loc = result["geometry"]["location"]

    zipcode = county = state = city_guess = None
    for comp in result["address_components"]:
        if "postal_code" in comp["types"]:
            zipcode = comp["long_name"]
        if "administrative_area_level_2" in comp["types"]:
            county = comp["long_name"]
        if "administrative_area_level_1" in comp["types"]:
            state = comp["short_name"]
        if "locality" in comp["types"]:
            city_guess = comp["long_name"]

    return loc["lat"], loc["lng"], zipcode, county, state, city_guess, "OK"


# ---------------- FEATURE SERVER QUERY ----------------
def query_feature_service(url, lat, lng, fallback_name=None, field_candidates=("NAME", "CITY", "CITY_NAME")):
    if "FeatureServer" not in url and "MapServer" not in url:
        return None

    params = {
        "f": "json",
        "geometry": f'{{"x": {lng}, "y": {lat}}}',
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false"
    }

    try:
        r = requests.get(url.rstrip("/") + "/query", params=params, timeout=15).json()
    except Exception:
        return None

    if "features" in r and r["features"]:
        attrs = r["features"][0]["attributes"]
        for field in field_candidates:
            if field in attrs and attrs[field]:
                return attrs[field]
        if fallback_name:
            return fallback_name
        return "City boundary match (no name field)"
    return None


# ---------------- RESOLVER ----------------
def get_official_city(lat, lng, county, google_city):
    # Step 1: County endpoint first (broad coverage)
    if county in COUNTY_ENDPOINTS and COUNTY_ENDPOINTS[county]:
        entry = COUNTY_ENDPOINTS[county]
        url = entry.get("url")
        fallback_name = entry.get("fallback_name")
        city = query_feature_service(url, lat, lng, fallback_name=fallback_name)
        if city:
            return city + " (county endpoint)"

    # Step 2: City endpoint as override (if explicitly defined)
    if google_city in CITY_ENDPOINTS and CITY_ENDPOINTS[google_city]:
        entry = CITY_ENDPOINTS[google_city]
        url = entry.get("url")
        fallback_name = entry.get("fallback_name")
        city = query_feature_service(url, lat, lng, fallback_name=fallback_name)
        if city:
            return city + " (city endpoint override)"

    # Step 3: Not available
    if google_city:
        return "(Authoritative Boundary Not Available)"
    return f"Not available / Unincorporated {county}"


# ---------------- STREAMLIT UI ----------------
st.title("🏙️ California Address Lookup")
st.write("Enter an address in California to get coordinates, ZIP, county, and official city boundary check.")

address = st.text_input("Address:")

if st.button("Lookup"):
    if not address.strip():
        st.error("⚠️ Please enter an address.")
    else:
        lat, lng, zipcode, county, state, city_guess, status = geocode_address(address, GOOGLE_KEY)
        if status != "OK":
            st.error(f"❌ Geocoding failed: {status}")
        elif state != "CA":
            st.warning(f"⚠️ The address is in {state}, not California.")
        else:
            official_city = get_official_city(lat, lng, county, city_guess)
            st.success("✅ Address found!")
            st.write(f"**Coordinates:** {lat}, {lng}")
            st.write(f"**ZIP Code:** {zipcode if zipcode else 'Unknown'}")
            st.write(f"**City:** {official_city}")
            st.write(f"**County:** {county if county else 'Unknown'}")