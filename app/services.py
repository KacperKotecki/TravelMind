# app/services.py
from .api_clients import get_weather, get_attractions, get_exchange_rate

# KROK 1: Tymczasowa, uproszczona baza danych kosztów dziennych (w EUR)
# W przyszłości te dane będą pochodzić z bazy danych.
CITY_COSTS = {
    "Paryż": {
        "waluta": "EUR",
        "Ekonomiczny": {"nocleg": 35, "wyzywienie": 30, "atrakcje": 15, "transport": 10},
        "Standardowy": {"nocleg": 80, "wyzywienie": 60, "atrakcje": 40, "transport": 15},
        "Komfortowy": {"nocleg": 200, "wyzywienie": 120, "atrakcje": 80, "transport": 40},
    },
    "Rzym": {
        "waluta": "EUR",
        "Ekonomiczny": {"nocleg": 30, "wyzywienie": 25, "atrakcje": 15, "transport": 8},
        "Standardowy": {"nocleg": 70, "wyzywienie": 50, "atrakcje": 35, "transport": 12},
        "Komfortowy": {"nocleg": 180, "wyzywienie": 100, "atrakcje": 70, "transport": 35},
    }
}

def get_plan_details(city: str, days: int, style: str) -> dict:
    """
    Główna funkcja serwisu, obsługująca dynamiczne miasta.
    """
    # KROK 1: Zawsze próbuj pobrać dane z zewnętrznych API
    weather_info = get_weather(city)
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
            "total_pln": round(total_cost_pln, 2) if total_cost_pln is not None else None,
            "total_local": round(total_cost_local, 2),
            "currency": city_data["waluta"]
        }
    else:
        # Jeśli nie mamy danych o kosztach, przygotuj pustą strukturę
        cost_info = {
            "total_pln": None,
            "total_local": None,
            "currency": None
        }

    # KROK 3: Zwrócenie ustrukturyzowanej odpowiedzi
    result = {
        "query": {"city": city, "days": days, "style": style},
        "cost": cost_info,
        "weather": weather_info or {"opis": "Brak danych pogodowych"},
        "attractions": attractions_list or [{"name": "Brak danych o atrakcjach"}]
    }
    
    return result
