# app/services.py

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
    Główna funkcja serwisu. Oblicza szczegóły planu podróży.
    Na tym etapie używa danych tymczasowych.
    """
    if city not in CITY_COSTS:
        # Prosta obsługa błędu, gdy miasto nie jest obsługiwane
        return {"error": f"Przepraszamy, miasto '{city}' nie jest jeszcze obsługiwane."}

    city_data = CITY_COSTS[city]
    style_data = city_data.get(style)

    if not style_data:
        return {"error": f"Nieprawidłowy styl podróży: '{style}'."}

    # KROK 2: Obliczenia
    daily_cost = sum(style_data.values())
    total_cost_local = daily_cost * days

    # KROK 3: Tymczasowe przeliczenie waluty (założenie 1 EUR = 4.3 PLN)
    # W przyszłości ta funkcja zostanie zastąpiona wywołaniem API.
    exchange_rate_pln = 4.3 
    total_cost_pln = total_cost_local * exchange_rate_pln

    # KROK 4: Tymczasowe dane pogodowe i atrakcje
    # Zostaną zastąpione przez wywołania API (Geoapify, OpenWeatherMap).
    weather_info = {"temperatura": 15, "opis": "Częściowe zachmurzenie"}
    attractions_list = [
        {"name": "Główna atrakcja miasta 1"},
        {"name": "Popularne muzeum"},
        {"name": "Znany zabytek"}
    ]
    
    # KROK 5: Zwrócenie ustrukturyzowanej odpowiedzi
    result = {
        "query": {"city": city, "days": days, "style": style},
        "cost": {
            "total_pln": round(total_cost_pln, 2),
            "total_local": round(total_cost_local, 2),
            "currency": city_data["waluta"]
        },
        "weather": weather_info,
        "attractions": attractions_list
    }
    
    return result
