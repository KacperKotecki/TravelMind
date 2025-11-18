import random

def recommend_city(selected_tags: list, cities_list: list, budget_style: str = None) -> dict | None:
    """
    Rekomenduje miasto na podstawie wybranych tagów i opcjonalnie stylu budżetowego.

    Args:
        selected_tags (list): Lista tagów wybranych przez użytkownika (np. ["city_break", "beach_sun"]).
        cities_list (list): Lista słowników reprezentujących miasta (z pliku JSON).
        budget_style (str, optional): Styl podróży ("Ekonomiczny", "Standardowy", "Komfortowy").
                                      Jeśli "Ekonomiczny", odrzuca miasta z cost_tier="high".

    Returns:
        dict | None: Wylosowany obiekt miasta spełniający kryteria lub None, jeśli brak pasujących miast.
    """
    if not cities_list or not selected_tags:
        return None

    # Krok 1: Filtrowanie po tagach
    # Miasto musi mieć PRZYNAJMNIEJ JEDEN z wybranych tagów
    filtered_cities = [
        city for city in cities_list
        if any(tag in city.get('tags', []) for tag in selected_tags)
    ]

    # Krok 2: Opcjonalne filtrowanie po budżecie
    if budget_style == "Ekonomiczny":
        # Odrzucamy miasta bardzo drogie (cost_tier: "high")
        filtered_cities = [
            city for city in filtered_cities
            if city.get('cost_tier') != 'high'
        ]

    # Jeśli po filtrowaniu lista jest pusta, zwracamy None
    if not filtered_cities:
        return None

    # Krok 3: Losowanie miasta
    return random.choice(filtered_cities)
