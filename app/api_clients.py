# app/api_clients.py
import requests
from flask import current_app

def get_weather(city: str) -> dict | None:
    """
    Pobiera aktualne dane pogodowe dla danego miasta z OpenWeatherMap.
    """
    api_key = current_app.config['OPENWEATHERMAP_API_KEY']
    if not api_key:
        current_app.logger.error("Brak klucza API dla OpenWeatherMap!")
        return None
    
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",  # Aby otrzymać temperaturę w Celsjuszach
        "lang": "pl"        # Aby otrzymać opis po polsku
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Rzuci wyjątkiem dla kodów błędu 4xx/5xx

        data = response.json()
        
        # Wyciągamy tylko potrzebne nam dane
        weather_details = {
            "temperatura": round(data['main']['temp']),
            "opis": data['weather'][0]['description'].capitalize()
        }
        return weather_details

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania do OpenWeatherMap API: {e}")
        return None
    except KeyError:
        current_app.logger.error(f"Nieoczekiwana struktura odpowiedzi z OpenWeatherMap dla miasta: {city}")
        return None


def get_coordinates_for_city(city: str) -> dict | None:
    """
    Pobiera współrzędne geograficzne (szerokość i długość) dla danego miasta.
    """
    api_key = current_app.config['GEOAPIFY_API_KEY']
    if not api_key:
        current_app.logger.error("Brak klucza API dla Geoapify!")
        return None

    base_url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": city,
        "format": "json",
        "apiKey": api_key,
        "limit": 1
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get('results'):
            current_app.logger.warning(f"Nie znaleziono współrzędnych dla miasta: {city}")
            return None

        location = data['results'][0]
        return {"lat": location['lat'], "lon": location['lon']}

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania Geocoding API: {e}")
        return None


def get_attractions(city: str, limit: int = 5) -> list | None:
    """
    Pobiera listę atrakcji dla danego miasta z Geoapify, używając dynamicznych współrzędnych.
    """
    # KROK 1: Pobierz dynamicznie współrzędne
    coords = get_coordinates_for_city(city)
    if not coords:
        return [] # Zwróć pustą listę, jeśli nie znaleziono miasta

    lon = coords['lon']
    lat = coords['lat']

    api_key = current_app.config['GEOAPIFY_API_KEY']
    if not api_key:
        current_app.logger.error("Brak klucza API dla Geoapify!")
        return None
    
    base_url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": "tourism.sights",
        "filter": f"circle:{lon},{lat},5000", # W promieniu 5km od znalezionego centrum
        "bias": f"proximity:{lon},{lat}",
        "limit": limit,
        "apiKey": api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        attractions = []
        for feature in data.get('features', []):
            properties = feature.get('properties', {})
            attraction_name = properties.get('name')
            # Czasem lepsza nazwa jest w 'name_alias'
            if not attraction_name:
                attraction_name = properties.get('name_alias', {}).get('default')

            if attraction_name:
                attractions.append({"name": attraction_name})
        
        return attractions

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania do Geoapify Places API: {e}")
        return None

def get_exchange_rate(base_currency: str, target_currency: str = "PLN") -> float | None:
    """
    Pobiera aktualny kurs wymiany walut.
    TODO: Zaimplementować wywołanie do API kursów walut.
    """
    # Tymczasowy, sztywny kurs
    if base_currency == "EUR" and target_currency == "PLN":
        return 4.3
    return None
