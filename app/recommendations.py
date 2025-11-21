import random
from collections import defaultdict

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

def get_grouped_recommendations(selected_tags: list, cities_list: list, budget_style: str = None) -> dict:
    """
    Zwraca słownik pogrupowany krajami z listą miast spełniających kryteria.
    Struktura: { "Kraj": [miasto1, miasto2, ...], ... }
    Maksymalnie 4 kraje, w każdym maksymalnie 4 miasta.
    """
    if not cities_list or not selected_tags:
        return {}

    # 1. Filtrowanie
    filtered_cities = [
        city for city in cities_list
        if any(tag in city.get('tags', []) for tag in selected_tags)
    ]

    if budget_style == "Ekonomiczny":
        filtered_cities = [c for c in filtered_cities if c.get('cost_tier') != 'high']

    if not filtered_cities:
        return {}

    # 2. Grupowanie po kraju
    grouped = defaultdict(list)
    for city in filtered_cities:
        country = city.get('country', 'Inne')
        grouped[country].append(city)

    # 3. Wybór krajów (max 4)
    all_countries = list(grouped.keys())
    random.shuffle(all_countries)
    selected_countries = all_countries[:4]

    # 4. Wybór miast w krajach (max 4)
    result = {}
    for country in selected_countries:
        cities_in_country = grouped[country]
        # Preferujmy różnorodność, więc shuffle
        random.shuffle(cities_in_country)
        result[country] = cities_in_country[:4]

    return result
