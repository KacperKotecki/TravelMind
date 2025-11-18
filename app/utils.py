from thefuzz import process, fuzz

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
