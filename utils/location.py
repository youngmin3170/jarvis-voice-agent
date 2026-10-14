import os
import re
import requests

def get_default_location_name() -> str:
    """Retrieves default city/location string from environment variables."""
    return os.getenv("DEFAULT_LOCATION", "Seoul")

def get_geocoding(location: str = None) -> tuple[float, float, str, str]:
    """
    Fetches latitude, longitude, city, and country for a location name.
    Tries Open-Meteo first. If it misses (common for specific neighborhoods),
    it falls back to OpenStreetMap (Nominatim).
    """
    if not location or location.strip().lower() in ["here", "my location", "current location"]:
        location = get_default_location_name()
        print(f"[J.A.R.V.I.S. Internal]: Resolving default location -> '{location}'")
        
    has_korean = bool(re.search(r'[가-힣]', location))
    lang_param = "&language=ko" if has_korean else ""
    if has_korean:
        print(f"[J.A.R.V.I.S. Internal]: Detected Korean characters in location '{location}'. Using Korean language parameter for geocoding.")
    
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1{lang_param}"
        geo_res = requests.get(geo_url, timeout=5).json()
        
        if "results" in geo_res and geo_res["results"]:
            lat = geo_res["results"][0]["latitude"]
            lon = geo_res["results"][0]["longitude"]
            city = geo_res["results"][0]["name"]
            country = geo_res["results"][0].get("country", "")
            return lat, lon, city, country
    except Exception:
        pass # Ignore failure, let it drop down to the fallback

    print(f"[J.A.R.V.I.S. Internal]: Primary geocoding missed. Querying OpenStreetMap for '{location}'...")
    try:
        osm_url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
        # OpenStreetMap requires a User-Agent header so they know who is calling
        headers = {"User-Agent": "JARVIS-Assistant/1.0"} 
        osm_res = requests.get(osm_url, headers=headers, timeout=5).json()
        
        if osm_res:
            lat = float(osm_res[0]["lat"])
            lon = float(osm_res[0]["lon"])
            
            # OSM returns a long display name (e.g., "Gwanpyeong-dong, Yuseong-gu, Daejeon, South Korea")
            full_name = osm_res[0].get("display_name", location)
            
            # Clean it up nicely for J.A.R.V.I.S. to read
            parts = full_name.split(",")
            city = parts[0].strip()
            country = parts[-1].strip() if len(parts) > 1 else ""
            
            return lat, lon, city, country

        raise Exception(f"Location '{location}' not found in any database.")
        
    except Exception as e:
        raise Exception(f"Geocoding completely failed for '{location}': {e}")