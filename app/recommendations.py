import random
from collections import defaultdict

def recommend_city(selected_tags: list, cities_list: list, budget_style: str = None) -> dict | None:
    """
    Wybiera jedno rekomendowane miasto na podstawie preferencji użytkownika (algorytm losujący).

    Funkcja filtruje dostępną bazę miast, szukając takich, które posiadają 
    przynajmniej jeden z wybranych tagów. Jeśli wybrano styl "Ekonomiczny",
    dodatkowo odrzucane są miasta flgowane jako drogie (`cost_tier: high`).

    Args:
        selected_tags (list): Lista stringów z tagami (np. ["beach_sun", "history"]).
        cities_list (list): Pełna lista słowników z danymi miast (zwykle z pliku JSON).
        budget_style (str, optional): Styl podróży. Wartość "Ekonomiczny" aktywuje filtr cenowy.

    Returns:
        dict | None: Losowo wybrany obiekt miasta spełniający kryteria 
                     lub None, jeśli żadne miasto nie pasuje do filtrów.
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
    Generuje zestaw rekomendacji pogrupowanych według krajów, idealny do widoków typu "Odkrywaj".

    W przeciwieństwie do `recommend_city`, ta funkcja zwraca wiele wyników.
    Aby zapewnić różnorodność i nie przytłoczyć użytkownika, wyniki są tasowane (shuffle),
    a ich liczba jest limitowana (max 4 kraje, max 4 miasta na kraj).

    Args:
        selected_tags (list): Lista tagów preferencji użytkownika.
        cities_list (list): Pełna lista dostępnych miast.
        budget_style (str, optional): Filtr budżetowy ("Ekonomiczny" odrzuca drogie miasta).

    Returns:
        dict: Słownik, gdzie kluczem jest nazwa kraju, a wartością lista obiektów miast.
              Przykład:
              {
                  "Włochy": [{"city": "Rzym", ...}, {"city": "Mediolan", ...}],
                  "Hiszpania": [{"city": "Barcelona", ...}]
              }
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
