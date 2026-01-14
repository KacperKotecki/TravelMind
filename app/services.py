from datetime import date, timedelta, datetime
from app.api import get_weather, get_attractions, get_coordinates_for_city
from .constants import BASE_COSTS, WEATHERCODE_TO_KEY, ICON_TO_EMOJI
from app.models import Country

def get_plan_details(city: str, days: int, style: str, country: str = None, start_date=None, end_date=None, lat: float = None, lon: float = None, cost_mult: float = 1.2) -> dict:
    """
    Agreguje szczegółowe dane dla planu podróży z zewnętrznych API (pogoda, atrakcje) i oblicza koszty.

    Funkcja pobiera dane pogodowe dla zadanego zakresu dat, przetwarza kody pogody na ikony/emotikony,
    pobiera listę atrakcji turystycznych oraz wylicza szacunkowy koszt wyjazdu na podstawie stylu podróży.
    
    Args:
        city (str): Nazwa miasta docelowego.
        days (int): Czas trwania podróży w dniach.
        style (str): Wybrany styl podróży (klucz do mapy BASE_COSTS, np. 'low_budget').
        country (str, optional): Nazwa kraju (ułatwia wyszukiwanie atrakcji).
        start_date (str/date, optional): Data początkowa (ISO format lub obiekt date).
        end_date (str/date, optional): Data końcowa (ISO format lub obiekt date).
        lat (float, optional): Szerokość geograficzna miasta (dla dokładniejszej pogody).
        lon (float, optional): Długość geograficzna miasta (dla dokładniejszej pogody).
        cost_mult (float, optional): Mnożnik kosztów specyficzny dla danego kraju/miasta. Domyślnie 1.2.

    Returns:
        dict: Słownik zawierający komplet danych planu:
            - 'query': Metadane zapytania (miasto, daty, styl).
            - 'cost': Obliczone koszty (PLN + waluta lokalna).
            - 'weather': Przetworzone dane pogodowe z ikonami.
            - 'attractions': Lista atrakcji turystycznych.
            - 'center': Współrzędne geograficzne (jeśli podano).
    """
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
    Zarządza procesem tworzenia planu podróży: waliduje dane wejściowe, wywołuje serwisy i sprawdza reguły biznesowe.

    Pełni rolę warstwy pośredniej (facade) między kontrolerem (Route) a logiką pobierania danych (`get_plan_details`).
    Odpowiada za przygotowanie (rzutowanie) typów danych z żądania HTTP oraz sprawdzenie, czy kraj jest bezpieczny (baza danych).

    Args:
        city (str): Nazwa miasta przesłana z formularza.
        days (int): Liczba dni przesłana z formularza.
        style (str): Styl podróży przesłany z formularza.
        query_params (dict): Słownik dodatkowych parametrów (np. `request.args`), zawierający:
            - 'cost_mult': Mnożnik kosztów (oczekiwany float).
            - 'country': Nazwa kraju.
            - 'start', 'end': Daty podróży.
            - 'lat', 'lon': Współrzędne geograficzne.

    Returns:
        dict: Struktura odpowiedzi dla widoku:
            - 'data': Wygenerowany plan podróży (dict) lub komunikat błędu.
            - 'status': Kod statusu HTTP (200 dla sukcesu, 404 dla błędu).
            - 'error': Opcjonalny opis błędu.
            W przypadku niebezpiecznego kraju, do 'data' dodawana jest flaga 'is_dangerous'.
    """
    
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