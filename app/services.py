# app/services.py
from datetime import date, timedelta, datetime
from .api_clients import get_weather, get_attractions, get_exchange_rate, get_coordinates_for_city
from .constans import BASE_COSTS, WEATHERCODE_TO_KEY, ICON_TO_EMOJI

def get_plan_details(city: str, days: int, style: str, start_date=None, end_date=None, lat: float = None, lon: float = None, cost_mult: float = 1.2) -> dict:
    """
    Główna funkcja serwisu, obsługująca dynamiczne miasta.
    """
    # Normalizuj nazwę miasta
    if isinstance(city, str):
        city = city.strip()

    # Uproszczona obsługa dat
    # Jeśli daty nie są podane, generujemy domyślny zakres od dzisiaj
    if not start_date or not end_date:
        start = date.today()
        days_int = int(days)
        end = start + timedelta(days=max(days_int - 1, 0))
        start_date = start.isoformat()
        end_date = end.isoformat()
    
    # Upewnij się, że days jest intem
    days = int(days)

    # Pobierz pogodę
    weather_info = get_weather(city, start_date=start_date, end_date=end_date, lat=lat, lon=lon)

    # Przetwarzanie pogody (ikony)
    if weather_info and isinstance(weather_info, dict):
        daily = weather_info.get('daily')
        if isinstance(daily, list):
            for d in daily:
                # Przypisz icon_key
                code = d.get('weathercode')
                if code is not None:
                    d['icon_key'] = WEATHERCODE_TO_KEY.get(int(code), 'unknown')
                else:
                    d['icon_key'] = 'unknown'
                
                # Przypisz icon_emoji
                key = d.get('icon_key')
                d['icon_emoji'] = ICON_TO_EMOJI.get(key, '🌤️')

            # top-level icon_key
            if daily:
                first = daily[0]
                if 'icon_key' in first:
                    weather_info['icon_key'] = first.get('icon_key')
    
    # Pobierz atrakcje (SSR)
    attractions_list = get_attractions(city, limit=12) or []

    # Obliczanie kosztów
    # Używamy BASE_COSTS z constants.py oraz cost_mult przekazanego w argumencie (z destinations.json)
    base_rate = BASE_COSTS.get(style, 500) # Domyślnie Standardowy
    
    # Obliczenie: Koszt = Stawka Bazowa * Mnożnik Miasta * Liczba Dni
    total_cost_pln = int(base_rate * cost_mult * days)
    
    cost_info = {
        "total_pln": total_cost_pln,
        "total_local": total_cost_pln, 
        "currency": "PLN",
    }

    # Zwrócenie odpowiedzi
    result = {
        "query": {"city": city, "days": days, "style": style, "start": start_date, "end": end_date},
        "cost": cost_info,
        "weather": weather_info or {"opis": "Brak danych pogodowych"},
        "attractions": attractions_list,
        "nearby_places": [], 
    }

    # Dodaj współrzędne centrum (jeśli dostępne)
    if lat is not None and lon is not None:
        result['center'] = {'lat': lat, 'lon': lon}

    return result
