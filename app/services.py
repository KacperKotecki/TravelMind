# app/services.py
from .api_clients import get_weather, get_attractions, get_exchange_rate, get_nearby_places, get_coordinates_for_city

# KROK 1: Tymczasowa, uproszczona baza danych kosztów dziennych (w EUR)
# W przyszłości te dane będą pochodzić z bazy danych.
CITY_COSTS = {
    "Paryż": {
        "waluta": "EUR",
        "Ekonomiczny": {
            "nocleg": 35,
            "wyzywienie": 30,
            "atrakcje": 15,
            "transport": 10,
        },
        "Standardowy": {
            "nocleg": 80,
            "wyzywienie": 60,
            "atrakcje": 40,
            "transport": 15,
        },
        "Komfortowy": {
            "nocleg": 200,
            "wyzywienie": 120,
            "atrakcje": 80,
            "transport": 40,
        },
    },
    "Rzym": {
        "waluta": "EUR",
        "Ekonomiczny": {"nocleg": 30, "wyzywienie": 25, "atrakcje": 15, "transport": 8},
        "Standardowy": {
            "nocleg": 70,
            "wyzywienie": 50,
            "atrakcje": 35,
            "transport": 12,
        },
        "Komfortowy": {
            "nocleg": 180,
            "wyzywienie": 100,
            "atrakcje": 70,
            "transport": 35,
        },
    },
}


def get_plan_details(city: str, days: int, style: str, start_date=None, end_date=None, lat: float = None, lon: float = None, cost_mult: float = 1.2) -> dict:
    """
    Główna funkcja serwisu, obsługująca dynamiczne miasta.
    """
    # Normalizuj nazwę miasta (usuń białe znaki na początku/końcu)
    if isinstance(city, str):
        city = city.strip()

    # KROK 1: Przygotuj zakres dat dla pogody i wymuś maksymalnie 16 dni (jeśli użytkownik poda zakres lub days)
    max_days = 16
    from datetime import date, timedelta, datetime

    # Jeśli użytkownik podał start_date i end_date, spróbuj je sparsować i przyciąć do max_days
    try:
        if start_date and end_date:
            # oczekujemy formatu YYYY-MM-DD lub obiektów date/datetime
            if isinstance(start_date, str):
                s_date = datetime.fromisoformat(start_date).date()
            elif isinstance(start_date, datetime):
                s_date = start_date.date()
            else:
                s_date = start_date

            if isinstance(end_date, str):
                e_date = datetime.fromisoformat(end_date).date()
            elif isinstance(end_date, datetime):
                e_date = end_date.date()
            else:
                e_date = end_date

            # jeśli zakres jest odwrotny, zamień
            if e_date < s_date:
                s_date, e_date = e_date, s_date

            requested_days = (e_date - s_date).days + 1
            if requested_days > max_days:
                # przytnij koniec zakresu
                e_date = s_date + timedelta(days=max_days - 1)
            start_date = s_date.isoformat()
            end_date = e_date.isoformat()
            days = min(int(days), max_days)
        else:
            # jeśli nie podano zakresu dat, wygeneruj od dziś na podstawie days (ogranicz do max_days)
            start = date.today()
            days_int = min(int(days), max_days)
            end = start + timedelta(days=max(days_int - 1, 0))
            start_date = start.isoformat()
            end_date = end.isoformat()
            days = days_int
    except Exception:
        # W razie problemów pozostaw wartości None aby get_weather mógł próbować fallback
        start_date = start_date
        end_date = end_date

    # KROK 1: Zawsze próbuj pobrać dane z zewnętrznych API
    # Przekaż współrzędne do get_weather jeśli zostały dostarczone (unikanie dodatkowego geokodowania)
    weather_info = get_weather(city, start_date=start_date, end_date=end_date, lat=lat, lon=lon)

    # Mapowanie kodów pogodowych -> klucze ikon SVG (server-side)
    weathercode_to_key = {
        0: 'clear',
        1: 'partly-cloudy',
        2: 'partly-cloudy',
        3: 'cloudy',
        45: 'fog',
        48: 'fog',
        51: 'drizzle',
        53: 'drizzle',
        55: 'drizzle',
        56: 'drizzle',
        57: 'drizzle',
        61: 'rain',
        63: 'rain',
        65: 'rain',
        66: 'rain',
        67: 'rain',
        71: 'snow',
        73: 'snow',
        75: 'snow',
        77: 'snow',
        80: 'rain',
        81: 'rain',
        82: 'rain',
        85: 'snow',
        86: 'snow',
        95: 'thunder',
        96: 'thunder',
        99: 'thunder'
    }

    # Jeśli mamy listę dni pogodowych, przypisz icon_key na podstawie weathercode
    if weather_info and isinstance(weather_info, dict):
        daily = weather_info.get('daily')
        if isinstance(daily, list):
            for d in daily:
                try:
                    code = d.get('weathercode')
                    if code is not None:
                        d['icon_key'] = weathercode_to_key.get(int(code), 'unknown')
                except Exception:
                    d['icon_key'] = 'unknown'
            # Mapowanie icon_key -> emoji (fallback, server-side)
            icon_to_emoji = {
                'clear': '☀️',
                'partly-cloudy': '⛅',
                'cloudy': '☁️',
                'fog': '🌫️',
                'drizzle': '🌦️',
                'rain': '🌧️',
                'snow': '❄️',
                'thunder': '⛈️',
                'unknown': '🌤️'
            }
            for d in daily:
                try:
                    key = d.get('icon_key')
                    if key:
                        d['icon_emoji'] = icon_to_emoji.get(key, '🌤️')
                    else:
                        d['icon_emoji'] = d.get('icon_emoji') or '🌤️'
                except Exception:
                    d['icon_emoji'] = '🌤️'
            # top-level icon_key (dla kompatybilności/widoku ogólnego)
            if daily:
                first = daily[0]
                if 'icon_key' in first:
                    weather_info['icon_key'] = first.get('icon_key')
    
    # KROK 1.5: Nie pobieramy atrakcji synchronicznie, aby nie blokować ładowania strony.
    # Dane o atrakcjach zostaną pobrane asynchronicznie przez JavaScript z endpointu /api/attractions/<city>
    attractions_list = [] 

    # Jeśli mamy współrzędne (lub możemy je pobrać), spróbuj znaleźć miejsca w promieniu 30 km
    nearby = None
    try:
        use_lat = lat
        use_lon = lon
        if use_lat is None or use_lon is None:
            coords = get_coordinates_for_city(city)
            if coords:
                use_lat = coords.get("lat")
                use_lon = coords.get("lon")

        if use_lat is not None and use_lon is not None:
            nearby = get_nearby_places(use_lat, use_lon, radius_km=30, limit=12)
    except Exception:
        nearby = None

    # KROK 2: Obliczanie kosztów (Nowa Logika)
    # Bazowe koszty dzienne w PLN dla różnych stylów podróży (mnożnik 1.0)
    # Te wartości powinny być zsynchronizowane z tymi w routes.py lub przeniesione do configu
    BASE_COSTS = {
        "Ekonomiczny": 250,
        "Standardowy": 500,
        "Komfortowy": 1000
    }
    
    base_rate = BASE_COSTS.get(style, 500) # Domyślnie Standardowy
    
    # Obliczenie: Koszt = Stawka Bazowa * Mnożnik Miasta * Liczba Dni
    total_cost_pln = int(base_rate * cost_mult * days)
    
    # Dla uproszczenia zakładamy, że waluta lokalna to też PLN lub przeliczamy (tutaj zostawiamy PLN jako główną)
    # W przyszłości można dodać API kursów walut
    cost_info = {
        "total_pln": total_cost_pln,
        "total_local": total_cost_pln, # Tymczasowo to samo
        "currency": "PLN",
    }

    # KROK 3: Zwrócenie ustrukturyzowanej odpowiedzi (bez atrakcji)
    result = {
        "query": {"city": city, "days": days, "style": style, "start": start_date, "end": end_date},
        "cost": cost_info,
        "weather": weather_info or {"opis": "Brak danych pogodowych"},
        "attractions": [],  # Zwracamy pustą listę, bo dane załaduje JS
        "nearby_places": nearby or [],
    }

    # Dodaj współrzędne centrum (jeśli dostępne) aby mapy mogły się wycentrować
    try:
        if 'use_lat' in locals() and use_lat is not None and 'use_lon' in locals() and use_lon is not None:
            result['center'] = {'lat': use_lat, 'lon': use_lon}
    except Exception:
        pass

    return result
