# app/api_clients.py
import requests
from flask import current_app

def _weather_code_to_polish(code: int) -> str:
    """Mapuje kod pogodowy Open-Meteo na opis po polsku.

    Źródło kodów: https://open-meteo.com/en/docs#weathercode
    """
    mapping = {
        0: 'Bezchmurnie',
        1: 'Częściowo słonecznie',
        2: 'Częściowo pochmurnie',
        3: 'Pochmurnie',
        45: 'Mgła',
        48: 'Osadzanie mroźnej mgły',
        51: 'Słabe mżawki',
        53: 'Umiarkowane mżawki',
        55: 'Gwałtowne mżawki',
        56: 'Słabe mżawki (zamarzające)',
        57: 'Gwałtowne mżawki (zamarzające)',
        61: 'Lekki deszcz',
        63: 'Umiarkowany deszcz',
        65: 'Silny deszcz',
        66: 'Słaby deszcz (zamarzający)',
        67: 'Silny deszcz (zamarzający)',
        71: 'Lekki śnieg',
        73: 'Umiarkowany śnieg',
        75: 'Silny śnieg',
        77: 'Opady śniegu (grudki)',
        80: 'Przelotne opady deszczu',
        81: 'Częste przelotne opady deszczu',
        82: 'Silne przelotne opady deszczu',
        85: 'Przelotne opady śniegu',
        86: 'Silne przelotne opady śniegu',
        95: 'Burze',
        96: 'Burze z gradem (słabe)',
        99: 'Burze z gradem (silne)'
    }
    return mapping.get(code, 'Nieznane warunki pogodowe')


def _weather_code_to_icon(code: int) -> str:
    """Mapuje kod pogodowy Open-Meteo na prostą ikonę (emoji)."""
    icons = {
        0: '☀️',
        1: '🌤️',
        2: '⛅',
        3: '☁️',
        45: '🌫️',
        48: '🌫️',
        51: '🌧️',
        53: '🌧️',
        55: '🌧️',
        56: '🌧️',
        57: '🌧️',
        61: '🌦️',
        63: '🌧️',
        65: '⛈️',
        66: '🌧️',
        67: '🌧️',
        71: '🌨️',
        73: '🌨️',
        75: '❄️',
        77: '❄️',
        80: '🌦️',
        81: '🌧️',
        82: '🌧️',
        85: '🌨️',
        86: '🌨️',
        95: '⛈️',
        96: '⛈️',
        99: '⛈️'
    }
    try:
        return icons.get(int(code), '🔆')
    except Exception:
        return '🔆'


def _format_date_val(val):
    # Akceptujemy daty jako obiekty date/datetime lub jako string YYYY-MM-DD
    from datetime import date, datetime
    if val is None:
        return None
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, datetime):
        return val.date().isoformat()
    # załóżmy że jest to już string
    return str(val)


def get_weather(city: str, start_date=None, end_date=None) -> dict | None:
    """Pobiera dane pogodowe dla danego miasta.

    Jeśli przekazano start_date i end_date (YYYY-MM-DD lub obiekty date),
    pobierz dane dzienne z Open-Meteo dla całego zakresu (daily arrays).
    Zwraca strukturę zawierającą 'daily': [ {date, temperatura_min, temperatura_max, opis, opad, wiatr} , ... ]
    W przypadku braku zakresu zachowuje częściową kompatybilność z poprzednią implementacją (current_weather + daily dla bieżącego dnia).
    """
    # Najpierw pobierz współrzędne (Geoapify)
    coords = get_coordinates_for_city(city)
    if not coords:
        current_app.logger.warning(f"Nie udało się pobrać współrzędnych dla: {city}")
        return None

    lat = coords.get('lat')
    lon = coords.get('lon')
    if lat is None or lon is None:
        current_app.logger.error(f"Nieprawidłowe współrzędne dla miasta: {city} -> {coords}")
        return None

    base_url = "https://api.open-meteo.com/v1/forecast"

    s = _format_date_val(start_date)
    e = _format_date_val(end_date)

    # Jeśli mamy zakres dat - poprośmy o daily dla zakresu
    if s and e:
        # 'time' is not a valid daily variable for the API params (it's returned automatically),
        # so do not include it in the 'daily' parameter.
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
            "start_date": s,
            "end_date": e,
            "timezone": "auto",
            "temperature_unit": "celsius"
        }
    else:
        # fallback: jak wcześniej - current weather + some daily
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "relativehumidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "temperature_unit": "celsius"
        }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            # Jeśli serwer zwrócił treść błędu, zaloguj ją — pomaga debugować 400/422 itp.
            try:
                body = response.text
            except Exception:
                body = '<brak treści odpowiedzi>'
            current_app.logger.error(f"Błąd podczas zapytania do Open-Meteo: {http_err} - body: {body}")
            return None
        data = response.json()

        # Jeśli poproszono o zakres dat - skonstruuj listę dni
        if s and e:
            daily = data.get('daily', {})
            times = daily.get('time', [])
            t_max = daily.get('temperature_2m_max', [])
            t_min = daily.get('temperature_2m_min', [])
            precip = daily.get('precipitation_sum', [])
            codes = daily.get('weathercode', [])
            wind = daily.get('windspeed_10m_max', [])

            daily_list = []
            for i, d in enumerate(times):
                item = {'date': d}
                try:
                    if i < len(t_max):
                        item['temperatura_max'] = round(float(t_max[i]))
                    if i < len(t_min):
                        item['temperatura_min'] = round(float(t_min[i]))
                    if i < len(precip):
                        item['opad_mm'] = round(float(precip[i]), 2)
                    if i < len(codes):
                        item['weathercode'] = int(codes[i])
                        item['opis'] = _weather_code_to_polish(int(codes[i]))
                        # ikonka pogody (emoji)
                        item['icon'] = _weather_code_to_icon(int(codes[i]))
                    if i < len(wind):
                        try:
                            # Open-Meteo wind in m/s? for 10m it's m/s; convert to km/h
                            item['wiatr_kmh'] = round(float(wind[i]) * 3.6, 1)
                        except Exception:
                            pass
                except Exception:
                    pass
                # Formatowanie etykiety daty bez roku (np. '2 lis') dla widoku
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(d)
                    month_names = {
                        1: 'sty', 2: 'lut', 3: 'mar', 4: 'kwi', 5: 'maj', 6: 'cze',
                        7: 'lip', 8: 'sie', 9: 'wrz', 10: 'paź', 11: 'lis', 12: 'gru'
                    }
                    item['date_label'] = f"{dt.day} {month_names.get(dt.month, '')}"
                except Exception:
                    # fallback: usuń rok z ISO 'YYYY-MM-DD' -> 'MM-DD' albo zostaw oryginał bez roku
                    try:
                        parts = str(d).split('-')
                        if len(parts) >= 3:
                            item['date_label'] = f"{int(parts[2])} {parts[1]}"
                        else:
                            item['date_label'] = d
                    except Exception:
                        item['date_label'] = d

                daily_list.append(item)

            # Przygotuj wynik z listą dni
            result = {'daily': daily_list}
            # Dla kompatybilności dodaj 'temperatura' jako średnią z pierwszego dnia jeśli dostępna
            if daily_list:
                first = daily_list[0]
                if 'temperatura_max' in first and 'temperatura_min' in first:
                    result['temperatura'] = round((first['temperatura_max'] + first['temperatura_min']) / 2)
                # add icon for first day for backward compatibility
                if 'icon' in first:
                    result['icon'] = first.get('icon')
            return result

        # fallback: zachowaj wcześniejszy przepływ jeśli nie było zakresu
        current = data.get('current_weather')
        if not current:
            current_app.logger.warning(f"Brak current_weather w odpowiedzi Open-Meteo dla: {city}")
            return None

        temp = current.get('temperature')
        code = current.get('weathercode')
        if temp is None or code is None:
            current_app.logger.error(f"Niepełne dane pogodowe od Open-Meteo dla: {city} -> {current}")
            return None

        # Spróbuj odczytać wilgotność z sekcji 'hourly' dopasowując czas
        humidity = None
        hourly = data.get('hourly')
        if hourly:
            times = hourly.get('time', [])
            humidities = hourly.get('relativehumidity_2m', [])

            from datetime import datetime, timezone

            def _parse_iso_iso(s: str):
                if not s:
                    return None
                try:
                    if s.endswith('Z'):
                        s2 = s[:-1] + '+00:00'
                    else:
                        s2 = s
                    dt = datetime.fromisoformat(s2)
                    return dt
                except Exception:
                    try:
                        return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
                    except Exception:
                        return None

            cur_time = _parse_iso_iso(current.get('time'))
            parsed_times = [ _parse_iso_iso(t) for t in times ]
            indexed = [(i, t) for i, t in enumerate(parsed_times) if t is not None]
            if cur_time is not None and indexed:
                def _to_utc_naive(dt):
                    if dt.tzinfo is not None:
                        return dt.astimezone(timezone.utc).replace(tzinfo=None)
                    return dt

                cur_naive = _to_utc_naive(cur_time)
                best_i = None
                best_diff = None
                for i, t in indexed:
                    t_naive = _to_utc_naive(t)
                    diff = abs((t_naive - cur_naive).total_seconds())
                    if best_diff is None or diff < best_diff:
                        best_diff = diff
                        best_i = i

                if best_i is not None and best_i < len(humidities):
                    humidity = humidities[best_i]
                else:
                    current_app.logger.info(f"Nie udało się dopasować wilgotności dla czasu: {current.get('time')}")

        description = _weather_code_to_polish(int(code))
        result = {"temperatura": round(float(temp)), "opis": description}
        try:
            result['icon'] = _weather_code_to_icon(int(code))
        except Exception:
            pass
        daily = data.get('daily')
        if daily:
            d_times = daily.get('time', [])
            d_max = daily.get('temperature_2m_max', [])
            d_min = daily.get('temperature_2m_min', [])
            try:
                from datetime import datetime

                cur_date = None
                ct = current.get('time')
                if ct:
                    cur_date = str(ct).split('T')[0]

                if cur_date and d_times:
                    if cur_date in d_times:
                        idx = d_times.index(cur_date)
                    else:
                        parsed = []
                        for i, s in enumerate(d_times):
                            try:
                                parsed.append((i, datetime.fromisoformat(s)))
                            except Exception:
                                continue
                        try:
                            cur_dt = datetime.fromisoformat(cur_date)
                            best = None
                            best_diff = None
                            for i, dt in parsed:
                                diff = abs((dt.date() - cur_dt.date()).days)
                                if best_diff is None or diff < best_diff:
                                    best_diff = diff
                                    best = i
                            idx = best
                        except Exception:
                            idx = None

                    if idx is not None and idx < len(d_max) and idx < len(d_min):
                        try:
                            result['temperatura_max'] = round(float(d_max[idx]))
                            result['temperatura_min'] = round(float(d_min[idx]))
                        except (TypeError, ValueError):
                            pass
            except Exception:
                pass
        if humidity is not None:
            try:
                result['wilgotnosc'] = round(float(humidity))
            except (TypeError, ValueError):
                pass

        windspeed = current.get('windspeed')
        if windspeed is not None:
            try:
                result['wiatr_kmh'] = round(float(windspeed), 1)
            except (TypeError, ValueError):
                pass

        return result

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania do Open-Meteo: {e}")
        return None


def get_coordinates_for_city(city: str) -> dict | None:
    """
    Pobiera współrzędne geograficzne (szerokość i długość) dla danego miasta.
    """
    # Najpierw spróbuj Geoapify, ale jeśli klucz jest nieprawidłowy lub brak wyników,
    # spróbuj automatycznie geokodowania przez Open-Meteo (bez klucza).
    api_key = current_app.config.get('GEOAPIFY_API_KEY')
    if api_key:
        base_url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            "text": city,
            "format": "json",
            "apiKey": api_key,
            "limit": 1
        }

        try:
            response = requests.get(base_url, params=params, timeout=8)
            # Jeśli autoryzacja nie przeszła, zaloguj i spróbuj fallback
            if response.status_code == 401:
                current_app.logger.warning("Geoapify zwrócił 401 Unauthorized - spróbuję fallback geokodowania.")
            else:
                response.raise_for_status()
                data = response.json()
                if data.get('results'):
                    location = data['results'][0]
                    return {"lat": location['lat'], "lon": location['lon']}
                else:
                    current_app.logger.info(f"Geoapify: brak wyników dla miasta: {city}")

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Błąd podczas zapytania Geoapify Geocoding API: {e}")

    # Fallback: Open-Meteo geocoding (nie wymaga klucza)
    try:
        om_url = "https://geocoding-api.open-meteo.com/v1/search"
        om_params = {"name": city, "count": 1, "language": "pl"}
        om_resp = requests.get(om_url, params=om_params, timeout=8)
        om_resp.raise_for_status()
        om_data = om_resp.json()
        results = om_data.get('results')
        if not results:
            current_app.logger.warning(f"Open-Meteo geocoding: brak wyników dla miasta: {city}")
            return None
        first = results[0]
        # Open-Meteo zwraca pola 'latitude' i 'longitude'
        lat = first.get('latitude')
        lon = first.get('longitude')
        if lat is None or lon is None:
            current_app.logger.error(f"Open-Meteo geocoding: niepełne dane dla: {city} -> {first}")
            return None
        return {"lat": lat, "lon": lon}

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania Open-Meteo Geocoding API: {e}")
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
