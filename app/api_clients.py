# app/api_clients.py
import re
import unicodedata
import requests
from functools import lru_cache
from flask import current_app


def _weather_code_to_polish(code: int) -> str:
    """Mapuje kod pogodowy Open-Meteo na opis po polsku.

    Źródło kodów: https://open-meteo.com/en/docs#weathercode
    """
    mapping = {
        0: "Bezchmurnie",
        1: "Częściowo słonecznie",
        2: "Częściowo pochmurnie",
        3: "Pochmurnie",
        45: "Mgła",
        48: "Osadzanie mroźnej mgły",
        51: "Słabe mżawki",
        53: "Umiarkowane mżawki",
        55: "Gwałtowne mżawki",
        56: "Słabe mżawki (zamarzające)",
        57: "Gwałtowne mżawki (zamarzające)",
        61: "Lekki deszcz",
        63: "Umiarkowany deszcz",
        65: "Silny deszcz",
        66: "Słaby deszcz (zamarzający)",
        67: "Silny deszcz (zamarzający)",
        71: "Lekki śnieg",
        73: "Umiarkowany śnieg",
        75: "Silny śnieg",
        77: "Opady śniegu (grudki)",
        80: "Przelotne opady deszczu",
        81: "Częste przelotne opady deszczu",
        82: "Silne przelotne opady deszczu",
        85: "Przelotne opady śniegu",
        86: "Silne przelotne opady śniegu",
        95: "Burze",
        96: "Burze z gradem (słabe)",
        99: "Burze z gradem (silne)",
    }
    return mapping.get(code, "Nieznane warunki pogodowe")


def _weather_code_to_icon(code: int) -> str:
    """Mapuje kod pogodowy Open-Meteo na prostą ikonę (emoji)."""
    icons = {
        0: "☀️",
        1: "🌤️",
        2: "⛅",
        3: "☁️",
        45: "🌫️",
        48: "🌫️",
        51: "🌧️",
        53: "🌧️",
        55: "🌧️",
        56: "🌧️",
        57: "🌧️",
        61: "🌦️",
        63: "🌧️",
        65: "⛈️",
        66: "🌧️",
        67: "🌧️",
        71: "🌨️",
        73: "🌨️",
        75: "❄️",
        77: "❄️",
        80: "🌦️",
        81: "🌧️",
        82: "🌧️",
        85: "🌨️",
        86: "🌨️",
        95: "⛈️",
        96: "⛈️",
        99: "⛈️",
    }
    try:
        return icons.get(int(code), "🔆")
    except Exception:
        return "🔆"


def _weather_code_to_key(code: int) -> str:
    """Zwraca krótki klucz opisowy dla typu pogody, przydatny do CSS/ikonek."""
    mapping = {
        0: "clear",
        1: "partly-sunny",
        2: "partly-cloudy",
        3: "cloudy",
        45: "fog",
        48: "fog",
        51: "drizzle",
        53: "drizzle",
        55: "drizzle",
        56: "freezing-drizzle",
        57: "freezing-drizzle",
        61: "rain",
        63: "rain",
        65: "heavy-rain",
        66: "freezing-rain",
        67: "freezing-rain",
        71: "snow",
        73: "snow",
        75: "heavy-snow",
        77: "snow-grains",
        80: "showers",
        81: "showers",
        82: "showers-heavy",
        85: "snow-showers",
        86: "snow-showers",
        95: "thunder",
        96: "thunder-hail",
        99: "thunder-hail",
    }
    try:
        return mapping.get(int(code), "unknown")
    except Exception:
        return "unknown"


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


def normalize_to_ascii(s: str) -> str:
    """Prosta transliteracja do ASCII: Łódź -> Lodz"""
    if not s:
        return s
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def build_geocode_variants(raw: str) -> list:
    """Zwraca listę wariantów zapytania geokodującego w kolejności próby.

    Przykład:
      'Łódź, Województwo łódzkie, Polska' -> ['Łódź, Województwo łódzkie, Polska', 'Łódź', 'Lodz']
    """
    if not raw:
        return []

    s = str(raw).strip()
    if not s:
        return []

    # znormalizuj wielokrotne spacje
    s = re.sub(r"\s+", " ", s)

    variants = []
    # pełny (oryginalny)
    variants.append(s)

    # pierwszy token przed przecinkiem (zwykle nazwa miasta)
    first = s.split(",")[0].strip()
    if first and first not in variants:
        variants.append(first)

    # usuń typy administracyjne (heurystyka)
    admin_words = [
        r"\bwojew[dóo]ztwo\b",
        r"\bpowiat\b",
        r"\bgmina\b",
        r"\bregion\b",
        r"\bmiasto\b",
        r"\bwoj\b",
        r"\bpolska\b",
        r"\bpoland\b",
    ]
    pattern = re.compile("|".join(admin_words), flags=re.IGNORECASE)
    first_clean = pattern.sub("", first).strip()
    first_clean = re.sub(r"\s+", " ", first_clean)
    if first_clean and first_clean not in variants:
        variants.append(first_clean)

    # transliteracja ASCII
    first_ascii = normalize_to_ascii(first_clean)
    if first_ascii and first_ascii not in variants:
        variants.append(first_ascii)

    return variants


def get_weather(
    city: str = None,
    start_date=None,
    end_date=None,
    lat: float = None,
    lon: float = None,
) -> dict | None:
    """Pobiera dane pogodowe dla danego miasta.

    Jeśli przekazano start_date i end_date (YYYY-MM-DD lub obiekty date),
    pobierz dane dzienne z Open-Meteo dla całego zakresu (daily arrays).
    Zwraca strukturę zawierającą 'daily': [ {date, temperatura_min, temperatura_max, opis, opad, wiatr} , ... ]
    W przypadku braku zakresu zachowuje częściową kompatybilność z poprzednią implementacją (current_weather + daily dla bieżącego dnia).
    """
    # Jeśli współrzędne (lat, lon) nie zostały przekazane, spróbuj je uzyskać z nazwy miasta
    if lat is None or lon is None:
        if not city:
            current_app.logger.error(
                "get_weather: brak 'city' oraz współrzędnych 'lat'/'lon'"
            )
            return None

        coords = get_coordinates_for_city(city)
        if not coords:
            current_app.logger.warning(
                f"Nie udało się pobrać współrzędnych dla: {city}"
            )
            return None

        lat = coords.get("lat")
        lon = coords.get("lon")

    # Sprawdzenie, czy na pewno mamy współrzędne
    if lat is None or lon is None:
        current_app.logger.error(
            f"Nieprawidłowe lub brakujące współrzędne dla zapytania pogodowego (miasto: {city})"
        )
        return None

    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        # Poprośmy też o hourly relative humidity oraz daily min/max temperatury
        "hourly": "relativehumidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
        "temperature_unit": "celsius",
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
                body = "<brak treści odpowiedzi>"
            current_app.logger.error(
                f"Błąd podczas zapytania do Open-Meteo: {http_err} - body: {body}"
            )

            # Próba automatycznego dopasowania zakresu dat jeśli API wskazuje ograniczony zakres
            # (np. "Parameter 'start_date' is out of allowed range from 2025-08-01 to 2025-11-17")
            retried_success = False
            try:
                if (
                    response.status_code == 400
                    and body
                    and "out of allowed range" in body
                ):
                    import re

                    m = re.search(
                        r"from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", body
                    )
                    if m:
                        allowed_start = m.group(1)
                        allowed_end = m.group(2)
                        # jeśli mieliśmy s/e to spróbuj je przyciąć do zakresu i ponowić zapytanie
                        if s and e:
                            from datetime import datetime

                            try:
                                req_s = datetime.fromisoformat(s).date()
                                req_e = datetime.fromisoformat(e).date()
                                a_s = datetime.fromisoformat(allowed_start).date()
                                a_e = datetime.fromisoformat(allowed_end).date()
                                # przytnij
                                new_s = max(req_s, a_s)
                                new_e = min(req_e, a_e)
                                if new_s <= new_e:
                                    params["start_date"] = new_s.isoformat()
                                    params["end_date"] = new_e.isoformat()
                                else:
                                    # Żądany zakres nie pokrywa się z dozwolonym zakresem.
                                    # W takim wypadku pobierzemy pełny dozwolony zakres zwrócony przez API.
                                    params["start_date"] = a_s.isoformat()
                                    params["end_date"] = a_e.isoformat()
                                    current_app.logger.info(
                                        f"Przycinam zakres dat do dozwolonego przez API: {params['start_date']} - {params['end_date']} i ponawiam zapytanie"
                                    )
                                    # ponów zapytanie raz
                                    retry_resp = requests.get(
                                        base_url, params=params, timeout=10
                                    )
                                    try:
                                        retry_resp.raise_for_status()
                                    except requests.exceptions.HTTPError as http_err2:
                                        current_app.logger.error(
                                            f"Retry Open-Meteo failed: {http_err2} - body: {retry_resp.text}"
                                        )
                                    else:
                                        # zastąpiamy response danymi z retry i pozwalamy dalszemu kodowi je przetworzyć
                                        response = retry_resp
                                        retried_success = True

                            except Exception:
                                pass
            except Exception:
                pass
            # jeśli nie udało się naprawić i retry nie powiódł się, zwróć None
            if not retried_success:
                return None
        data = response.json()

        current = data.get("current_weather")
        if not current:
            current_app.logger.warning(
                f"Brak current_weather w odpowiedzi Open-Meteo dla: {city}"
            )
            return None

        temp = current.get("temperature")
        code = current.get("weathercode")
        if temp is None or code is None:
            current_app.logger.error(
                f"Niepełne dane pogodowe od Open-Meteo dla: {city} -> {current}"
            )
            return None

        # Spróbuj odczytać wilgotność z sekcji 'hourly' dopasowując czas
        humidity = None
        hourly = data.get("hourly")
        if hourly:
            times = hourly.get("time", [])
            humidities = hourly.get("relativehumidity_2m", [])

            from datetime import datetime, timezone

            def _parse_iso_iso(s: str):
                if not s:
                    return None
                try:
                    if s.endswith("Z"):
                        s2 = s[:-1] + "+00:00"
                    else:
                        s2 = s
                    dt = datetime.fromisoformat(s2)
                    return dt
                except Exception:
                    try:
                        # próbuj prostszych formatów
                        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        return None

            cur_time = _parse_iso_iso(current.get("time"))
            parsed_times = [_parse_iso_iso(t) for t in times]
            # Filtruj nieparowane wartości
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
                    current_app.logger.info(
                        f"Nie udało się dopasować wilgotności dla czasu: {current.get('time')}"
                    )

        description = _weather_code_to_polish(int(code))
        result = {"temperatura": round(float(temp)), "opis": description}
        # Spróbuj odczytać temperatury dzienne (min/max) z sekcji 'daily'
        daily = data.get("daily")
        if daily:
            d_times = daily.get("time", [])
            d_max = daily.get("temperature_2m_max", [])
            d_min = daily.get("temperature_2m_min", [])
            # Dopasuj dzień na podstawie current['time'] (data)
            try:
                from datetime import datetime

                cur_date = None
                ct = current.get("time")
                if ct:
                    # weź tylko część daty YYYY-MM-DD
                    cur_date = str(ct).split("T")[0]

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
                            result["temperatura_max"] = round(float(d_max[idx]))
                            result["temperatura_min"] = round(float(d_min[idx]))
                        except (TypeError, ValueError):
                            pass
            except Exception:
                pass
        if humidity is not None:
            try:
                result["wilgotnosc"] = round(float(humidity))
            except (TypeError, ValueError):
                pass

        # Dodaj informacje o wietrze jeśli są dostępne
        windspeed = current.get("windspeed")
        if windspeed is not None:
            try:
                result["wiatr_kmh"] = round(float(windspeed), 1)
            except (TypeError, ValueError):
                pass

        return result

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania do Open-Meteo: {e}")
        return None


@lru_cache(maxsize=256)
def get_coordinates_for_city(city: str) -> dict | None:
    """
    Pobiera współrzędne geograficzne (szerokość i długość) dla danego miasta.
    """
    # Najpierw spróbuj Geoapify, ale jeśli klucz jest nieprawidłowy lub brak wyników,
    # spróbuj automatycznie geokodowania przez Open-Meteo (bez klucza).
    api_key = current_app.config.get("GEOAPIFY_API_KEY")
    if api_key:
        base_url = "https://api.geoapify.com/v1/geocode/search"
        params = {"text": city, "format": "json", "apiKey": api_key, "limit": 1}

        try:
            response = requests.get(base_url, params=params, timeout=8)
            # Jeśli autoryzacja nie przeszła, zaloguj i spróbuj fallback
            if response.status_code == 401:
                current_app.logger.warning(
                    "Geoapify zwrócił 401 Unauthorized - spróbuję fallback geokodowania."
                )
            else:
                response.raise_for_status()
                data = response.json()
                if data.get("results"):
                    location = data["results"][0]
                    return {"lat": location["lat"], "lon": location["lon"]}
                else:
                    current_app.logger.info(
                        f"Geoapify: brak wyników dla miasta: {city}"
                    )

        except requests.exceptions.RequestException as e:
            current_app.logger.error(
                f"Błąd podczas zapytania Geoapify Geocoding API: {e}"
            )

    # Fallback: Open-Meteo geocoding (nie wymaga klucza)
    try:
        om_url = "https://geocoding-api.open-meteo.com/v1/search"
        om_params = {"name": city, "count": 1, "language": "pl"}
        om_resp = requests.get(om_url, params=om_params, timeout=8)
        om_resp.raise_for_status()
        om_data = om_resp.json()
        results = om_data.get("results")
        if not results:
            current_app.logger.warning(
                f"Open-Meteo geocoding: brak wyników dla miasta: {city}"
            )
            return None
        first = results[0]
        # Open-Meteo zwraca pola 'latitude' i 'longitude'
        lat = first.get("latitude")
        lon = first.get("longitude")
        if lat is None or lon is None:
            current_app.logger.error(
                f"Open-Meteo geocoding: niepełne dane dla: {city} -> {first}"
            )
            return None
        return {"lat": lat, "lon": lon}

    except requests.exceptions.RequestException as e:
        current_app.logger.error(
            f"Błąd podczas zapytania Open-Meteo Geocoding API: {e}"
        )
        return None


def get_attractions(city: str, limit: int = 5) -> list | None:
    """
    Pobiera listę atrakcji dla danego miasta z Google Places API.
    """
    api_key = current_app.config.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        current_app.logger.error("Brak klucza API dla Google Places!")
        return None
    current_app.logger.info("Klucz API Google Places został wczytany.")

    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    query = f"atrakcje w {city}"

    params = {
        "query": query,
        "key": api_key,
        "language": "pl",
    }
    current_app.logger.info(
        f"Wysyłanie zapytania do Google Places z parametrami: {params}"
    )

    try:
        response = requests.get(base_url, params=params, timeout=10)
        current_app.logger.info(
            f"Otrzymano odpowiedź od Google Places API. Status: {response.status_code}"
        )
        response.raise_for_status()
        data = response.json()
        current_app.logger.debug(f"Surowa odpowiedź z Google Places API: {data}")

        results = data.get("results", [])

        attractions = []
        for place in results[:limit]:
            attractions.append(
                {
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "rating": place.get("rating"),
                    "price_level": place.get("price_level"),
                    "types": place.get("types", []),
                    "icon": place.get("icon"),
                }
            )

        current_app.logger.info(
            f"Znaleziono i przetworzono {len(attractions)} atrakcji."
        )
        return attractions

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania do Google Places API: {e}")
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
