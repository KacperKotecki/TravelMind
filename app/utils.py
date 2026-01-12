from thefuzz import process, fuzz
import re
import unicodedata
from datetime import date, datetime

def normalize_city_name(user_input: str, cities_list: list, threshold: int = 75) -> dict | None:
    """
    Normalizuje nazwę miasta wpisaną przez użytkownika, znajdując najlepsze dopasowanie
    w liście miast z pliku JSON.

    Args:
        user_input (str): Tekst wpisany przez użytkownika (np. "krakow", "warsaw").
        cities_list (list): Lista słowników reprezentujących miasta (np. z pliku JSON).
                            Oczekuje, że każdy słownik ma klucz 'city'.
        threshold (int): Minimalny próg dopasowania (0-100). Domyślnie 75.

    Returns:
        dict | None: Pełny obiekt miasta z listy, jeśli znaleziono dopasowanie powyżej progu.
                     W przeciwnym razie None.
    """
    if not user_input or not cities_list:
        return None

    # Tworzymy mapę {nazwa_miasta: obiekt_miasta} dla łatwego dostępu po znalezieniu nazwy
    # Zakładamy, że w JSON klucz z nazwą miasta to 'city' (zgodnie z typową strukturą)
    # Jeśli klucz jest inny (np. 'name'), trzeba to dostosować.
    cities_map = {city_obj.get('city'): city_obj for city_obj in cities_list if city_obj.get('city')}
    
    # Lista samych nazw miast do przeszukania
    city_names = list(cities_map.keys())

    # Używamy process.extractOne do znalezienia najlepszego dopasowania
    # scorer=fuzz.token_sort_ratio jest dobry do ignorowania kolejności słów i wielkości liter
    best_match = process.extractOne(user_input, city_names, scorer=fuzz.token_sort_ratio)

    if best_match:
        matched_name, score = best_match
        
        if score >= threshold:
            return cities_map[matched_name]
    
    return None

def normalize_to_ascii(s: str) -> str:
    """Prosta transliteracja do ASCII: Łódź -> Lodz"""
    if not s:
        return s
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))

def format_date_val(val):
    """Formatuje datę do formatu YYYY-MM-DD wymaganego przez API."""
    if val is None:
        return None
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, datetime):
        return val.date().isoformat()
    return str(val)

def build_geocode_variants(raw: str) -> list:
    """Tworzy warianty nazwy miasta do geokodowania."""
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

    # Regexpy dla jednostek administracyjnych
    admin_words = [
        r"\bwojew[dóo]ztwo\b", r"\bpowiat\b", r"\bgmina\b",
        r"\bregion\b", r"\bmiasto\b", r"\bwoj\b",
        r"\bpolska\b", r"\bpoland\b",
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
