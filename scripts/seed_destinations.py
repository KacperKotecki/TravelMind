import json
import os
import sys

# Dodaj ścieżkę do katalogu nadrzędnego, aby zaimportować 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Destination

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
        print("Zapisywanie do bazy danych...")
        count = 0
        skipped = 0
        
        for item in data:
            # Sprawdź, czy taki wpis już istnieje (po nazwie i kraju)
            exists = Destination.query.filter_by(name=item['name'], country=item['country']).first()
            
            if not exists:
                dest = Destination(
                    name=item['name'],
                    country=item['country'],
                    tags=item['tags'],
                    cost_tier=item.get('cost_tier'),
                    cost_multiplier=item.get('cost_multiplier'),
                    image_keyword=item.get('image_keyword')
                )
                db.session.add(dest)
                count += 1
            else:
                skipped += 1
        
        try:
            db.session.commit()
            print(f"Sukces! Dodano {count} nowych miejsc. Pominięto {skipped} istniejących.")
        except Exception as e:
            db.session.rollback()
            print(f"Błąd zapisu do bazy: {e}")

if __name__ == '__main__':
    seed_destinations()