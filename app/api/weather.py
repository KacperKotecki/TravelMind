import requests
import re
from flask import current_app
from app.constans import WEATHER_CODES_PL
from .utils import format_date_val
from .places import get_coordinates_for_city

def _weather_code_to_polish(code: int) -> str:
    return WEATHER_CODES_PL.get(code, "Nieznane warunki pogodowe")

def get_weather(city: str = None, start_date=None, end_date=None, lat: float = None, lon: float = None) -> dict | None:
    # 1. Uzupełnienie współrzędnych jeśli brak
    if lat is None or lon is None:
        if not city:
            return None
        coords = get_coordinates_for_city(city)
        if not coords:
            return None
        lat, lon = coords.get("lat"), coords.get("lon")

    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": "relativehumidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "timezone": "auto",
        "temperature_unit": "celsius",
    }

    s = format_date_val(start_date)
    e = format_date_val(end_date)
    if s: params["start_date"] = s
    if e: params["end_date"] = e

    try:
        response = requests.get(base_url, params=params, timeout=10)
        
        # Obsługa błędu zakresu dat (prosta naprawa)
        if response.status_code == 400 and "out of allowed range" in response.text:
             # Tutaj uproszczony fallback: pobierz bez dat (domyślna prognoza)
             params.pop("start_date", None)
             params.pop("end_date", None)
             response = requests.get(base_url, params=params, timeout=10)

        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Open-Meteo Error: {e}")
        return None

    # Parsowanie wyniku
    current = data.get("current_weather", {})
    if not current:
        return None

    result = {
        "temperatura": round(float(current.get("temperature", 0))),
        "opis": _weather_code_to_polish(current.get("weathercode")),
        "wiatr_kmh": current.get("windspeed")
    }

    # Parsowanie dziennych (Daily)
    daily = data.get("daily", {})
    if daily:
        daily_list = []
        times = daily.get("time", [])
        codes = daily.get("weathercode", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rain = daily.get("precipitation_sum", [])
        
        for i, t in enumerate(times):
            day_obj = {"date": t}
            if i < len(max_temps): day_obj["temperatura_max"] = round(max_temps[i])
            if i < len(min_temps): day_obj["temperatura_min"] = round(min_temps[i])
            if i < len(rain): day_obj["opad_mm"] = rain[i]
            if i < len(codes): 
                day_obj["weathercode"] = codes[i]
                day_obj["opis"] = _weather_code_to_polish(codes[i])
            
            daily_list.append(day_obj)
        
        result["daily"] = daily_list

    return result