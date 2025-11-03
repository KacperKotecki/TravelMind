# app/services.py
from .api_clients import get_weather, get_attractions, get_exchange_rate

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


def get_plan_details(city: str, days: int, style: str, start_date=None, end_date=None, lat: float = None, lon: float = None) -> dict:
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
    attractions_list = get_attractions(city)

    # KROK 2: Sprawdź, czy mamy dane o kosztach dla tego miasta
    if city in CITY_COSTS:
        city_data = CITY_COSTS[city]
        style_data = city_data.get(style)

        if not style_data:
            # To zabezpieczenie na wypadek błędnego stylu, nawet dla znanego miasta
            return {"error": f"Nieprawidłowy styl podróży: '{style}'."}

        daily_cost = sum(style_data.values())
        total_cost_local = daily_cost * days

        exchange_rate_pln = get_exchange_rate(city_data["waluta"], "PLN")

        if not exchange_rate_pln:
            total_cost_pln = None
        else:
            total_cost_pln = total_cost_local * exchange_rate_pln

        cost_info = {
            "total_pln": (
                round(total_cost_pln, 2) if total_cost_pln is not None else None
            ),
            "total_local": round(total_cost_local, 2),
            "currency": city_data["waluta"],
        }
    else:
        # Jeśli nie mamy danych o kosztach, przygotuj pustą strukturę
        cost_info = {"total_pln": None, "total_local": None, "currency": None}

    # KROK 3: Zwrócenie ustrukturyzowanej odpowiedzi (bez atrakcji)
    result = {
        "query": {"city": city, "days": days, "style": style, "start": start_date, "end": end_date},
        "cost": cost_info,
        "weather": weather_info or {"opis": "Brak danych pogodowych"},
        "attractions": [],  # Zwracamy pustą listę, bo dane załaduje JS
    }

    return result
