import re
import unicodedata
from datetime import date, datetime

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