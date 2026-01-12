import os
import pytest
from app import create_app, db
from app.models import User

@pytest.fixture(scope='session')
def app():
    """Tworzy instancję aplikacji raz na całą sesję testową."""
    app = create_app('testing')
    
    # Konfiguracja ścieżki do bazy testowej
    test_db_path = os.path.join(app.root_path, 'app-test.db')

    yield app

    # Po zakończeniu wszystkich testów usuwamy plik bazy
    if os.path.exists(test_db_path):
        try:
            os.unlink(test_db_path)
        except Exception:
            pass

@pytest.fixture(scope='function')
def _db(app):
    """Zarządza bazą danych dla każdego testu z osobna (czyści dane)."""
    with app.app_context():
        db.create_all()  # Tworzy tabele przed każdym testem
        yield db
        db.session.remove()
        db.drop_all()    # Usuwa tabele i dane po każdym teście

@pytest.fixture
def client(app, _db):
    """Klient testowy (zależny od _db, aby baza była zawsze świeża)."""
    return app.test_client()

@pytest.fixture
def new_user(_db):
    """Tworzy użytkownika w świeżej bazie danych dla konkretnego testu."""
    u = User(email='testuser@example.com', first_name='Test', last_name='User')
    u.set_password('Test1234')
    db.session.add(u)
    db.session.commit()
    return u
