import json
import os
import sys

# Dodaj ścieżkę do katalogu nadrzędnego, aby zaimportować 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Country, City

def seed_destinations():
    app = create_app(os.getenv('FLASK_CONFIG') or 'development')
    
    # Zakładamy, że plik destinations.json jest w folderze app/plans/
    json_path = os.path.join(app.root_path, 'plans', 'destinations.json')
    
    if not os.path.exists(json_path):
        print(f"Błąd: Plik nie istnieje: {json_path}")
        return

    print(f"Wczytywanie danych z {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with app.app_context():
        print("Rozpoczynam aktualizację bazy danych...")
        
        # 1. Dodawanie Krajów (Country)
        # Pobieramy unikalne nazwy krajów z pliku JSON
        unique_countries = {item['country'] for item in data if item.get('country')}
        countries_added = 0
        
        for country_name in unique_countries:
            # Sprawdzamy czy kraj już istnieje
            if not Country.query.filter_by(name=country_name).first():
                db.session.add(Country(name=country_name))
                countries_added += 1
        
        # Zapisujemy kraje, aby mieć pewność, że istnieją i mają ID przed dodawaniem miast
        db.session.commit()
        print(f"Dodano {countries_added} nowych krajów.")

        # 2. Dodawanie Miast (City)
        cities_added = 0
        cities_skipped = 0
        
        for item in data:
            country_name = item.get('country')
            city_name = item.get('name')
            
            if not country_name or not city_name:
                continue

            # Pobieramy obiekt kraju z bazy
            country_obj = Country.query.filter_by(name=country_name).first()
            
            if country_obj:
                # Sprawdź, czy miasto już istnieje w tym kraju
                exists = City.query.filter_by(name=city_name, country_id=country_obj.id).first()
                
                if not exists:
                    city = City(
                        name=city_name,
                        country=country_obj, # SQLAlchemy automatycznie przypisze country_id
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