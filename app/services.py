from datetime import date, timedelta, datetime
from app.api import get_weather, get_attractions, get_coordinates_for_city
from .constants import BASE_COSTS, WEATHERCODE_TO_KEY, ICON_TO_EMOJI
from app.models import Country

def get_plan_details(city: str, days: int, style: str, country: str = None, start_date=None, end_date=None, lat: float = None, lon: float = None, cost_mult: float = 1.2) -> dict:
    """
    Główna funkcja serwisu, obsługująca dynamiczne miasta.
    """
    # Normalizuj nazwę miasta
    if isinstance(city, str):
        city = city.strip()

    # Uproszczona obsługa dat
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
    
    # Pobierz atrakcje (SSR) - TERAZ PRZEKAZUJEMY KRAJ
    # ZMIANA: Przekazujemy country do get_attractions
    attractions_list = get_attractions(city, country=country, limit=12) or []

    # Obliczanie kosztów
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
        "query": {"city": city, "country": country, "days": days, "style": style, "start": start_date, "end": end_date},
        "cost": cost_info,
        "weather": weather_info or {"opis": "Brak danych pogodowych"},
        "attractions": attractions_list,
        "nearby_places": [], 
    }

    # Dodaj współrzędne centrum (jeśli dostępne)
    if lat is not None and lon is not None:
        result['center'] = {'lat': lat, 'lon': lon}

    return result


def orchestrate_plan_creation(city, days, style, query_params):
    """
    Główna funkcja orkiestratora.
    Przyjmuje surowe dane, waliduje, pobiera dane (pogoda, atrakcje) 
    i zwraca kompletny obiekt planu lub słownik z błędem.
    """
    
    # 1. Walidacja parametrów wejściowych (to co było w routes)
    if isinstance(city, str):
        city = city.strip()
        
    cost_mult = query_params.get("cost_mult", 1.2)
    try:
        cost_mult = float(cost_mult)
    except (ValueError, TypeError):
        cost_mult = 1.2

    country_name = query_params.get("country")

    # 2. Wywołanie twojej istniejącej logiki (zakładam, że get_plan_details to ta funkcja)
    #    Możemy tu przekazać oczyszczone parametry.
    plan_data = get_plan_details(
        city, 
        days, 
        style, 
        country=country_name, 
        start_date=query_params.get("start"), 
        end_date=query_params.get("end"), 
        lat=query_params.get("lat"), 
        lon=query_params.get("lon"), 
        cost_mult=cost_mult
    )
    
    if plan_data.get("error"):
        return {"error": plan_data["error"], "status": 404}

    # 3. Logika biznesowa: Sprawdzanie bezpieczeństwa kraju (wyjęte z routes)
    if country_name:
        plan_data['query']['country'] = country_name
        
        country_obj = Country.query.filter_by(name=country_name).first()
        if country_obj and country_obj.danger:
            plan_data['is_dangerous'] = True
    
    return {"data": plan_data, "status": 200}