import json
import os
import sys

# Dodaj ścieżkę do katalogu nadrzędnego
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Country, City

# Lista krajów z informacją o bezpieczeństwie (na podstawie Twoich danych)
DANGER_LIST = [
  { "name": "Afganistan", "danger": "yes" },
  { "name": "Albania", "danger": "no" },
  { "name": "Algieria", "danger": "no" },
  { "name": "Andora", "danger": "no" },
  { "name": "Angola", "danger": "no" },
  { "name": "Antigua i Barbuda", "danger": "no" },
  { "name": "Arabia Saudyjska", "danger": "no" },
  { "name": "Argentyna", "danger": "no" },
  { "name": "Armenia", "danger": "no" },
  { "name": "Australia", "danger": "no" },
  { "name": "Austria", "danger": "no" },
  { "name": "Azerbejdżan", "danger": "no" },
  { "name": "Bahamy", "danger": "no" },
  { "name": "Bahrajn", "danger": "no" },
  { "name": "Bangladesz", "danger": "no" },
  { "name": "Barbados", "danger": "no" },
  { "name": "Belgia", "danger": "no" },
  { "name": "Belize", "danger": "no" },
  { "name": "Benin", "danger": "no" },
  { "name": "Bhutan", "danger": "no" },
  { "name": "Białoruś", "danger": "no" },
  { "name": "Boliwia", "danger": "no" },
  { "name": "Bośnia i Hercegowina", "danger": "no" },
  { "name": "Botswana", "danger": "no" },
  { "name": "Brazylia", "danger": "no" },
  { "name": "Brunei", "danger": "no" },
  { "name": "Bułgaria", "danger": "no" },
  { "name": "Burkina Faso", "danger": "no" },
  { "name": "Burundi", "danger": "no" },
  { "name": "Chile", "danger": "no" },
  { "name": "Chiny", "danger": "no" },
  { "name": "Chorwacja", "danger": "no" },
  { "name": "Cypr", "danger": "no" },
  { "name": "Czad", "danger": "no" },
  { "name": "Czarnogóra", "danger": "no" },
  { "name": "Czechy", "danger": "no" },
  { "name": "Dania", "danger": "no" },
  { "name": "Demokratyczna Republika Konga", "danger": "yes" },
  { "name": "Dominika", "danger": "no" },
  { "name": "Dominikana", "danger": "no" },
  { "name": "Dżibuti", "danger": "no" },
  { "name": "Egipt", "danger": "no" },
  { "name": "Ekwador", "danger": "no" },
  { "name": "Erytrea", "danger": "yes" },
  { "name": "Estonia", "danger": "no" },
  { "name": "Eswatini", "danger": "no" },
  { "name": "Etiopia", "danger": "no" },
  { "name": "Fidżi", "danger": "no" },
  { "name": "Filipiny", "danger": "no" },
  { "name": "Finlandia", "danger": "no" },
  { "name": "Francja", "danger": "no" },
  { "name": "Gabon", "danger": "no" },
  { "name": "Gambia", "danger": "no" },
  { "name": "Ghana", "danger": "no" },
  { "name": "Grecja", "danger": "no" },
  { "name": "Grenada", "danger": "no" },
  { "name": "Gruzja", "danger": "no" },
  { "name": "Gujana", "danger": "no" },
  { "name": "Gwatemala", "danger": "no" },
  { "name": "Gwinea", "danger": "no" },
  { "name": "Gwinea Bissau", "danger": "no" },
  { "name": "Gwinea Równikowa", "danger": "no" },
  { "name": "Haiti", "danger": "yes" },
  { "name": "Hiszpania", "danger": "no" },
  { "name": "Holandia", "danger": "no" },
  { "name": "Honduras", "danger": "no" },
  { "name": "Indie", "danger": "no" },
  { "name": "Indonezja", "danger": "no" },
  { "name": "Irak", "danger": "yes" },
  { "name": "Iran", "danger": "no" },
  { "name": "Irlandia", "danger": "no" },
  { "name": "Islandia", "danger": "no" },
  { "name": "Izrael", "danger": "yes" },
  { "name": "Jamajka", "danger": "no" },
  { "name": "Japonia", "danger": "no" },
  { "name": "Jemen", "danger": "yes" },
  { "name": "Jordania", "danger": "no" },
  { "name": "Kambodża", "danger": "no" },
  { "name": "Kamerun", "danger": "no" },
  { "name": "Kanada", "danger": "no" },
  { "name": "Katar", "danger": "no" },
  { "name": "Kazachstan", "danger": "no" },
  { "name": "Kenia", "danger": "no" },
  { "name": "Kirgistan", "danger": "no" },
  { "name": "Kiribati", "danger": "no" },
  { "name": "Kolumbia", "danger": "no" },
  { "name": "Komory", "danger": "no" },
  { "name": "Republika Konga", "danger": "no" },
  { "name": "Korea Północna", "danger": "no" },
  { "name": "Korea Południowa", "danger": "no" },
  { "name": "Kostaryka", "danger": "no" },
  { "name": "Kuba", "danger": "no" },
  { "name": "Kuwejt", "danger": "no" },
  { "name": "Laos", "danger": "no" },
  { "name": "Lesotho", "danger": "no" },
  { "name": "Liban", "danger": "no" },
  { "name": "Liberia", "danger": "no" },
  { "name": "Libia", "danger": "yes" },
  { "name": "Liechtenstein", "danger": "no" },
  { "name": "Litwa", "danger": "no" },
  { "name": "Luksemburg", "danger": "no" },
  { "name": "Łotwa", "danger": "no" },
  { "name": "Macedonia Północna", "danger": "no" },
  { "name": "Madagaskar", "danger": "no" },
  { "name": "Malawi", "danger": "no" },
  { "name": "Malediwy", "danger": "no" },
  { "name": "Malezja", "danger": "no" },
  { "name": "Mali", "danger": "yes" },
  { "name": "Malta", "danger": "no" },
  { "name": "Maroko", "danger": "no" },
  { "name": "Mauretania", "danger": "no" },
  { "name": "Mauritius", "danger": "no" },
  { "name": "Meksyk", "danger": "no" },
  { "name": "Mikronezja", "danger": "no" },
  { "name": "Mjanma", "danger": "no" },
  { "name": "Mołdawia", "danger": "no" },
  { "name": "Monako", "danger": "no" },
  { "name": "Mongolia", "danger": "no" },
  { "name": "Mozambik", "danger": "no" },
  { "name": "Namibia", "danger": "no" },
  { "name": "Nauru", "danger": "no" },
  { "name": "Nepal", "danger": "no" },
  { "name": "Niemcy", "danger": "no" },
  { "name": "Niger", "danger": "yes" },
  { "name": "Nigeria", "danger": "yes" },
  { "name": "Nikaragua", "danger": "no" },
  { "name": "Norwegia", "danger": "no" },
  { "name": "Nowa Zelandia", "danger": "no" },
  { "name": "Oman", "danger": "no" },
  { "name": "Pakistan", "danger": "no" },
  { "name": "Palau", "danger": "no" },
  { "name": "Panama", "danger": "no" },
  { "name": "Papua Nowa Gwinea", "danger": "no" },
  { "name": "Paragwaj", "danger": "no" },
  { "name": "Peru", "danger": "no" },
  { "name": "Polska", "danger": "no" },
  { "name": "RPA", "danger": "no" },
  { "name": "Portugalia", "danger": "no" },
  { "name": "Republika Środkowoafrykańska", "danger": "yes" },
  { "name": "Republika Zielonego Przylądka", "danger": "no" },
  { "name": "Rosja", "danger": "no" },
  { "name": "Rumunia", "danger": "no" },
  { "name": "Rwanda", "danger": "no" },
  { "name": "Saint Kitts i Nevis", "danger": "no" },
  { "name": "Saint Lucia", "danger": "no" },
  { "name": "Saint Vincent i Grenadyny", "danger": "no" },
  { "name": "Salwador", "danger": "no" },
  { "name": "Samoa", "danger": "no" },
  { "name": "San Marino", "danger": "no" },
  { "name": "Senegal", "danger": "no" },
  { "name": "Serbia", "danger": "no" },
  { "name": "Seszele", "danger": "no" },
  { "name": "Sierra Leone", "danger": "no" },
  { "name": "Singapur", "danger": "no" },
  { "name": "Słowacja", "danger": "no" },
  { "name": "Słowenia", "danger": "no" },
  { "name": "Somalia", "danger": "yes" },
  { "name": "Sri Lanka", "danger": "no" },
  { "name": "Stany Zjednoczone", "danger": "no" },
  { "name": "Sudan", "danger": "yes" },
  { "name": "Sudan Południowy", "danger": "yes" },
  { "name": "Surinam", "danger": "no" },
  { "name": "Syria", "danger": "yes" },
  { "name": "Szwajcaria", "danger": "no" },
  { "name": "Szwecja", "danger": "no" },
  { "name": "Tadżykistan", "danger": "no" },
  { "name": "Tajlandia", "danger": "no" },
  { "name": "Tanzania", "danger": "no" },
  { "name": "Timor Wschodni", "danger": "no" },
  { "name": "Togo", "danger": "no" },
  { "name": "Tonga", "danger": "no" },
  { "name": "Trynidad i Tobago", "danger": "no" },
  { "name": "Tunezja", "danger": "no" },
  { "name": "Turcja", "danger": "no" },
  { "name": "Turkmenistan", "danger": "no" },
  { "name": "Tuvalu", "danger": "no" },
  { "name": "Uganda", "danger": "no" },
  { "name": "Ukraina", "danger": "yes" },
  { "name": "Urugwaj", "danger": "no" },
  { "name": "Uzbekistan", "danger": "no" },
  { "name": "Vanuatu", "danger": "no" },
  { "name": "Watykan", "danger": "no" },
  { "name": "Wenezuela", "danger": "yes" },
  { "name": "Węgry", "danger": "no" },
  { "name": "Wielka Brytania", "danger": "no" },
  { "name": "Wietnam", "danger": "no" },
  { "name": "Włochy", "danger": "no" },
  { "name": "Wybrzeże Kości Słoniowej", "danger": "no" },
  { "name": "Wyspy Marshalla", "danger": "no" },
  { "name": "Wyspy Salomona", "danger": "no" },
  { "name": "Wyspy Świętego Tomasza i Książęca", "danger": "no" },
  { "name": "Zambia", "danger": "no" },
  { "name": "Zimbabwe", "danger": "no" },
  { "name": "Zjednoczone Emiraty Arabskie", "danger": "no" }
]

def seed_destinations():
    app = create_app(os.getenv('FLASK_CONFIG') or 'development')
    
    json_path = os.path.join(app.root_path, 'plans', 'destinations.json')
    
    if not os.path.exists(json_path):
        print(f"Błąd: Plik nie istnieje: {json_path}")
        return

    print(f"Wczytywanie danych z {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Tworzenie słownika do szybkiego sprawdzania statusu niebezpieczeństwa
    danger_map = {item['name']: (item['danger'] == 'yes') for item in DANGER_LIST}

    with app.app_context():
        print("Rozpoczynam aktualizację bazy danych...")
        
        # 1. Dodawanie Krajów
        unique_countries = {item['country'] for item in data if item.get('country')}
        countries_added = 0
        countries_updated = 0
        
        for country_name in unique_countries:
            country = Country.query.filter_by(name=country_name).first()
            is_dangerous = danger_map.get(country_name, False) # Domyślnie False jeśli brak w liście

            if not country:
                db.session.add(Country(name=country_name, danger=is_dangerous))
                countries_added += 1
            else:
                # Aktualizacja istniejącego kraju o status bezpieczeństwa
                if country.danger != is_dangerous:
                    country.danger = is_dangerous
                    countries_updated += 1
        
        db.session.commit()
        print(f"Dodano {countries_added} nowych krajów. Zaktualizowano {countries_updated} o status bezpieczeństwa.")

        # 2. Dodawanie Miast (bez zmian)
        cities_added = 0
        cities_skipped = 0
        
        for item in data:
            country_name = item.get('country')
            city_name = item.get('name')
            
            if not country_name or not city_name:
                continue

            country_obj = Country.query.filter_by(name=country_name).first()
            
            if country_obj:
                exists = City.query.filter_by(name=city_name, country_id=country_obj.id).first()
                
                if not exists:
                    city = City(
                        name=city_name,
                        country=country_obj,
                        tags=item.get('tags'),
                        cost_tier=item.get('cost_tier'),
                        cost_multiplier=item.get('cost_multiplier'),
                        image_keyword=item.get('image_keyword')
                    )
                    db.session.add(city)
                    cities_added += 1
                else:
                    cities_skipped += 1
            else:
                print(f"Ostrzeżenie: Nie znaleziono kraju '{country_name}' dla miasta '{city_name}'")
        
        try:
            db.session.commit()
            print(f"Sukces! Dodano {cities_added} nowych miast. Pominięto {cities_skipped} istniejących.")
        except Exception as e:
            db.session.rollback()
            print(f"Błąd zapisu do bazy: {e}")

if __name__ == '__main__':
    seed_destinations()