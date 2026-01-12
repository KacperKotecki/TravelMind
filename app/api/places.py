import requests
from flask import current_app
from functools import lru_cache
from app.constants import PLACE_TYPES_PL

# URL stale
GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

@lru_cache(maxsize=256)
def get_coordinates_for_city(city: str) -> dict | None:
    api_key = current_app.config.get("GEOAPIFY_API_KEY")
    
    # 1. Próba Geoapify
    if api_key:
        base_url = "https://api.geoapify.com/v1/geocode/search"
        params = {"text": city, "format": "json", "apiKey": api_key, "limit": 1}
        try:
            response = requests.get(base_url, params=params, timeout=8)
            if response.status_code != 401:
                response.raise_for_status()
                data = response.json()
                if data.get("results"):
                    location = data["results"][0]
                    return {"lat": location["lat"], "lon": location["lon"]}
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Geoapify Error: {e}")

    # 2. Fallback Open-Meteo Geocoding
    try:
        om_url = "https://geocoding-api.open-meteo.com/v1/search"
        om_params = {"name": city, "count": 1, "language": "pl"}
        om_resp = requests.get(om_url, params=om_params, timeout=8)
        om_resp.raise_for_status()
        om_data = om_resp.json()
        results = om_data.get("results")
        if results:
            first = results[0]
            return {"lat": first.get("latitude"), "lon": first.get("longitude")}
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Open-Meteo Geocoding Error: {e}")
        return None

    return None

def get_attractions(city: str, country: str = None, limit: int = 5) -> list[dict] | None:
    api_key = current_app.config.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        current_app.logger.error("Brak klucza API dla Google Places!")
        return None

    query_str = f"atrakcje w {city}"
    if country:
        query_str += f", {country}"

    params = {"query": query_str, "key": api_key, "language": "pl"}

    try:
        response = requests.get(GOOGLE_PLACES_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            return []

        results = data.get("results", [])
        return [_parse_place_data(place, api_key) for place in results[:limit]]

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Google Places API Error: {e}")
        return None

def _parse_place_data(place: dict, api_key: str) -> dict:
    geom = place.get("geometry", {})
    loc = geom.get("location", {})
    
    photo_url = None
    photos = place.get("photos", [])
    if photos:
        photo_ref = photos[0].get("photo_reference")
        if photo_ref:
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={api_key}"

    # Tłumaczenie typów
    raw_types = place.get("types", [])
    translated_types = [PLACE_TYPES_PL.get(t) for t in raw_types if PLACE_TYPES_PL.get(t)]
    if not translated_types and raw_types:
        translated_types.append(raw_types[0].replace("_", " ").capitalize())

    return {
        "name": place.get("name"),
        "address": place.get("formatted_address"),
        "rating": place.get("rating"),
        "price_level": place.get("price_level"),
        "types": translated_types,
        "icon": place.get("icon"),
        "photo_url": photo_url,
        "lat": loc.get("lat"),
        "lon": loc.get("lng"),
    }

def search_city_suggestions(query: str) -> list[dict]:
    """Wyszukuje sugestie miast używając Open-Meteo Geocoding."""
    if not query:
        return []
    try:
        om_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": query, "count": 6, "language": "pl"}
        resp = requests.get(om_url, params=params, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for r in data.get("results", []):
            name = r.get("name") or ""
            admin1 = r.get("admin1") or ""
            country = r.get("country") or ""
            display = name
            if admin1: display += f", {admin1}"
            if country: display += f", {country}"
            
            results.append({
                "name": display, 
                "lat": r.get("latitude"), 
                "lon": r.get("longitude")
            })
        return results
    except Exception as e:
        current_app.logger.error(f"Błąd wyszukiwania miast: {e}")
        return []