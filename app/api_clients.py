# app/api_clients.py
import re
import unicodedata
import requests
from functools import lru_cache
from flask import current_app
from .constans import WEATHER_CODES_PL, PLACE_TYPES_PL


def _weather_code_to_polish(code: int) -> str:
    """Mapuje kod pogodowy Open-Meteo na opis po polsku."""
    return WEATHER_CODES_PL.get(code, "Nieznane warunki pogodowe")


def _format_date_val(val):
    from datetime import date, datetime

    if val is None:
        return None
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, datetime):
        return val.date().isoformat()
    return str(val)


def normalize_to_ascii(s: str) -> str:
    """Prosta transliteracja do ASCII: Łódź -> Lodz"""
    if not s:
        return s
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def build_geocode_variants(raw: str) -> list:
    if not raw:
        return []

    s = str(raw).strip()
    if not s:
        return []

    s = re.sub(r"\s+", " ", s)

    variants = []
    variants.append(s)

    first = s.split(",")[0].strip()
    if first and first not in variants:
        variants.append(first)

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
        "hourly": "relativehumidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "timezone": "auto",
        "temperature_unit": "celsius",
    }

    s = _format_date_val(start_date)
    e = _format_date_val(end_date)
    if s:
        params["start_date"] = s
    if e:
        params["end_date"] = e

    try:
        response = requests.get(base_url, params=params, timeout=10)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            try:
                body = response.text
            except Exception:
                body = ""
            current_app.logger.error(f"Open-Meteo HTTPError: {http_err} - body: {body}")
            if body and "out of allowed range" in body:
                fixed = False
                if s and e:
                    m = re.search(r"from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", body)
                    if m:
                        allowed_start = m.group(1)
                        allowed_end = m.group(2)
                        try:
                            from datetime import datetime

                            req_s = datetime.fromisoformat(s).date()
                            a_s = datetime.fromisoformat(allowed_start).date()
                            a_e = datetime.fromisoformat(allowed_end).date()
                            new_s = max(req_s, a_s)
                            new_e = min(datetime.fromisoformat(e).date(), a_e)
                            if new_s <= new_e:
                                params["start_date"] = new_s.isoformat()
                                params["end_date"] = new_e.isoformat()
                                response = requests.get(base_url, params=params, timeout=10)
                                response.raise_for_status()
                                fixed = True
                        except Exception:
                            pass
                
                if not fixed:
                    params.pop("start_date", None)
                    params.pop("end_date", None)
                    params.pop("daily", None)
                    response = requests.get(base_url, params=params, timeout=10)
                    response.raise_for_status()
            else:
                return None
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd podczas zapytania do Open-Meteo: {e}")
        return None

    data = response.json()

    current = data.get("current_weather")
    if not current:
        current_app.logger.warning(f"Brak current_weather w odpowiedzi Open-Meteo dla: {city}")
        return None

    temp = current.get("temperature")
    code = current.get("weathercode")
    if temp is None or code is None:
        current_app.logger.error(f"Niepełne dane pogodowe od Open-Meteo dla: {city} -> {current}")
        return None

    humidity = None
    hourly = data.get("hourly")
    if hourly:
        times = hourly.get("time", [])
        humidities = hourly.get("relativehumidity_2m", [])
        try:
            from datetime import datetime, timezone

            def _parse_iso_iso(s: str):
                if not s:
                    return None
                try:
                    if s.endswith("Z"):
                        s2 = s[:-1] + "+00:00"
                    else:
                        s2 = s
                    return datetime.fromisoformat(s2)
                except Exception:
                    return None

            cur_time = _parse_iso_iso(current.get("time"))
            parsed_times = [_parse_iso_iso(t) for t in times]
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
        except Exception:
            pass

    description = _weather_code_to_polish(int(code))
    result = {"temperatura": round(float(temp)), "opis": description}

    daily_section = data.get("daily")
    if daily_section:
        d_times = daily_section.get("time", [])
        d_max = daily_section.get("temperature_2m_max", [])
        d_min = daily_section.get("temperature_2m_min", [])
        d_prec = daily_section.get("precipitation_sum", [])
        d_codes = daily_section.get("weathercode", [])
        d_wind = daily_section.get("windspeed_10m_max", [])

        daily_list = []
        for i, day_str in enumerate(d_times):
            day_obj = {"date": day_str}
            try:
                if i < len(d_min):
                    day_obj["temperatura_min"] = round(float(d_min[i]))
            except Exception:
                pass
            try:
                if i < len(d_max):
                    day_obj["temperatura_max"] = round(float(d_max[i]))
            except Exception:
                pass
            try:
                if i < len(d_prec):
                    day_obj["opad_mm"] = round(float(d_prec[i]), 1)
            except Exception:
                pass
            try:
                if i < len(d_wind):
                    day_obj["wiatr_kmh"] = round(float(d_wind[i]), 1)
            except Exception:
                pass
            try:
                if i < len(d_codes):
                    code_i = int(d_codes[i])
                    day_obj["weathercode"] = code_i
                    day_obj["opis"] = _weather_code_to_polish(code_i)
                else:
                    day_obj["opis"] = description
            except Exception:
                day_obj["opis"] = description

            daily_list.append(day_obj)

        result["daily"] = daily_list

    if humidity is not None:
        try:
            result["wilgotnosc"] = round(float(humidity))
        except (TypeError, ValueError):
            pass

    windspeed = current.get("windspeed")
    if windspeed is not None:
        try:
            result["wiatr_kmh"] = round(float(windspeed), 1)
        except (TypeError, ValueError):
            pass

    return result


@lru_cache(maxsize=256)
def get_coordinates_for_city(city: str) -> dict | None:
    api_key = current_app.config.get("GEOAPIFY_API_KEY")
    if api_key:
        base_url = "https://api.geoapify.com/v1/geocode/search"
        params = {"text": city, "format": "json", "apiKey": api_key, "limit": 1}

        try:
            response = requests.get(base_url, params=params, timeout=8)
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


GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"


# ZMIANA: Dodano parametr country z domyślną wartością None
def get_attractions(city: str, country: str = None, limit: int = 5) -> list[dict] | None:
    """Pobiera listę atrakcji dla danego miasta (i opcjonalnie kraju) z Google Places API."""
    api_key = current_app.config.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        current_app.logger.error("Brak klucza API dla Google Places!")
        return None
    current_app.logger.info("Klucz API Google Places został wczytany.")

    # Budujemy zapytanie uwzględniając kraj, jeśli jest podany
    query_str = f"atrakcje w {city}"
    if country:
        query_str += f", {country}"

    params = {
        "query": query_str,
        "key": api_key,
        "language": "pl",
    }
    current_app.logger.info(
        f"Wysyłanie zapytania do Google Places z parametrami: {params}"
    )

    try:
        response = requests.get(GOOGLE_PLACES_URL, params=params, timeout=20)
        current_app.logger.info(
            f"Otrzymano odpowiedź od Google Places API. Status HTTP: {response.status_code}"
        )
        response.raise_for_status()
        data = response.json()
        
        api_status = data.get("status")
        if api_status != "OK":
            error_msg = data.get("error_message", "Brak szczegółów")
            current_app.logger.error(f"Google Places API zwróciło błąd logiczny. Status: {api_status}, Komunikat: {error_msg}")
            if api_status == "ZERO_RESULTS":
                current_app.logger.info(f"Brak wyników dla zapytania: {params['query']}")
                return []
            return None

        current_app.logger.debug(f"Surowa odpowiedź z Google Places API: {data}")

        results = data.get("results", [])
        attractions = []

        for place in results[:limit]:
            attractions.append(_parse_place_data(place, api_key))

        current_app.logger.info(
            f"Prawidłowy klucz API. Pobrano {len(attractions)} obiektów z zapytania do API dla miasta: {city}, kraj: {country}."
        )
        return attractions

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Błąd sieciowy/HTTP podczas zapytania do Google Places API: {e}")
        return None


def _parse_place_data(place: dict, api_key: str) -> dict:
    """Pomocnicza funkcja do ekstrakcji danych pojedynczego miejsca."""
    geom = place.get("geometry", {})
    loc = geom.get("location", {})
    lat = loc.get("lat") if loc else None
    lon = loc.get("lng") if loc else None

    photo_url = None
    photos = place.get("photos", [])
    if photos:
        photo_ref = photos[0].get("photo_reference")
        if photo_ref:
            photo_url = (
                f"https://maps.googleapis.com/maps/api/place/photo"
                f"?maxwidth=400&photo_reference={photo_ref}&key={api_key}"
            )

    raw_types = place.get("types", [])
    translated_types = []
    for t in raw_types:
        pl_name = PLACE_TYPES_PL.get(t)
        if pl_name:
            translated_types.append(pl_name)

    if not translated_types and raw_types:
        translated_types.append(raw_types[0].replace("_", " ").capitalize())

    return {
        "name": place.get("name"),
        "address": place.get("formatted_address"),
        "rating": place.get("rating"),
        "price_level": place.get("price_level"),
        "types": translated_types, 
        "icon": place.get("icon"),
        "photo_url": photo_url,
        "lat": lat,
        "lon": lon,
    }


def get_exchange_rate(base_currency: str, target_currency: str = "PLN") -> float | None:
    if base_currency == "EUR" and target_currency == "PLN":
        return 4.3
    return None