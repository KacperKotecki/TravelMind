import requests
import re
from datetime import datetime, timedelta
from flask import current_app
from app.constants import WEATHER_CODES_PL
from app.utils import format_date_val
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

    # 2. PRZYGOTOWANIE PARAMETRÓW BAZOWYCH
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

    # 3. WALIDACJA DAT (Refaktoryzacja)
    
    use_dates = False
    date_warning_msg = None
    
    s_str = format_date_val(start_date)
    e_str = format_date_val(end_date)
    
    if s_str and e_str:
        try:
            today = datetime.now().date()
            d_start = datetime.strptime(s_str, "%Y-%m-%d").date()
            
            # Limit API (przyjmujemy 14 dni)
            max_future = today + timedelta(days=14)
            
            # Warunki: data zbyt stara lub zbyt daleko w przyszłość
            is_too_old = d_start < (today - timedelta(days=1)) 
            is_too_far = d_start > max_future
            
            if not is_too_old and not is_too_far:
                params["start_date"] = s_str
                params["end_date"] = e_str
                use_dates = True
            else:
                # --- LOGOWANIE OSTRZEŻENIA DLA DEVELOPERA ---
                current_app.logger.warning(
                    f"[Pogoda] Zignorowano daty dla miasta {city}. Żądana data: {s_str}. "
                    f"Powód: Poza zakresem API Open-Meteo (Max 14 dni w przód)."
                )
                # --- INFORMACJA DLA UŻYTKOWNIKA ---
                date_warning_msg = "Prognoza dotyczy najbliższych dni, ponieważ wybrana data podróży wykracza poza zakres prognozy długoterminowej."
                
        except ValueError:
            current_app.logger.error(f"[Pogoda] Błąd formatu daty dla miasta {city}: {s_str}")
            pass

    # 4. WYSŁANIE ŻĄDANIA
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status() 
        data = response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"[Pogoda] Błąd połączenia z Open-Meteo API: {e}")
        return None

    # 5. Parsowanie wyniku
    current = data.get("current_weather", {})
    if not current:
        return None

    result = {
        "temperatura": round(float(current.get("temperature", 0))),
        "opis": _weather_code_to_polish(current.get("weathercode")),
        "wiatr_kmh": current.get("windspeed"),
        # Przekazujemy ostrzeżenie do frontendu
        "warning_note": date_warning_msg
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
            if i < len(max_temps) and max_temps[i] is not None: day_obj["temperatura_max"] = round(max_temps[i])
            if i < len(min_temps) and min_temps[i] is not None: day_obj["temperatura_min"] = round(min_temps[i])
            if i < len(rain): day_obj["opad_mm"] = rain[i]
            if i < len(codes): 
                day_obj["weathercode"] = codes[i]
                day_obj["opis"] = _weather_code_to_polish(codes[i])
            
            daily_list.append(day_obj)
        
        result["daily"] = daily_list

    return result