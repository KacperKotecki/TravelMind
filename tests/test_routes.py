import pytest
import uuid
import json
from app import db
from app.models import User
from unittest.mock import patch  # symulacja działania API bez posiadania klucza

# --- TU ZACZYNAJĄ SIĘ TESTY ---

#PODSTAWOWE TESTY DOSTĘPNOŚCI STRON
def test_home_page(client):
    """Sprawdza czy strona główna zwraca kod 200"""
    response = client.get('/')
    assert response.status_code == 200


def test_page_not_exist(client):
    """Sprawdza czy nieistniejąca strona zwraca 404"""
    response = client.get('/strona-ktorej-nie-ma')
    assert response.status_code == 404

#TESTY AUTORYZACJI I KONTA UŻYTKOWNIKA
def test_register_login_logout(client):
    """Testuje pełny cykl rejestracji, logowania i wylogowania użytkownika"""
    # Rejestracja
    resp = client.post('/register', data={
        'first_name': 'Alicja',
        'last_name': 'Kowalska',
        'phone': '123456789',
        'email': 'alicja@gmail.com',
        'password': 'haslo1',
        'password2': 'haslo1'
    }, follow_redirects=True) #jeżeli zalogowano test również podąża dalej
    assert resp.status_code == 200
    assert b'Konto zosta' in resp.data or b'Konto zosta' in resp.data

    # Logowanie
    resp = client.post('/login', data={
        'email': 'alicja@gmail.com',
        'password': 'haslo1'
    }, follow_redirects=True)
    assert resp.status_code == 200

    # Dostęp do chronionej strony
    resp = client.get('/account')
    assert resp.status_code == 200

    # Wylogowanie
    resp = client.get('/logout', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Zosta\xc5\x82e\xc5\xb3 wylogowany' in resp.data or b'Zosta' in resp.data

# Testy negatywne autoryzacji
def test_login_incorrect_password(client, new_user):
    """Logowanie z błędnym hasłem powinno zwrócić błąd flash"""
    resp = client.post('/login', data={
        'email': new_user.email,
        'password': 'ZleHaslo123'
    }, follow_redirects=True)
    assert b'Nieprawid' in resp.data
    assert resp.status_code == 200

def test_protected_without_loggedin(client):
    """Anonimowy użytkownik powinien zostać przekierowany z chronionych stron"""
    resp = client.get('/profile')
    assert resp.status_code == 302
    assert '/login' in resp.headers.get('Location', '') #testuje dekorator @login_required


# TESTY GENERATORA PLANU PODRÓŻY
def test_plan_generator_with_city(client):
    """Sprawdza czy wysłanie formularza z miastem, datą i stylem działa poprawnie"""
    resp = client.post('/', data={
        'city': 'Warszawa',
        'date_range': '2026-05-01 - 2026-05-05',
        'travel_style': 'Standardowy',
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert '/plan/Warszawa/' in resp.headers['Location']

def test_plan_generator_with_vibes(client):
    """Sprawdza czy wysłanie formularza z "vibes" zamiast miasta działa poprawnie"""
    resp = client.post('/', data={
        'vibes': ['beach_sun', 'nature'],
        'date_range': '2026-05-01 - 2026-05-05',
        'travel_style': 'Ekonomiczny'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert 'Polecane' in resp.get_data(as_text=True)

def test_api_attractions_mocked(client):
    """Testuje endpoint atrakcji udając odpowiedź z API."""
    # Patchujemy funkcję get_attractions w pliku, w którym jest wywoływana
    with patch('app.plans.routes.get_attractions') as mocked_get:
        # Ustalamy, co ma zwrócić nasza "udawana" funkcja
        mocked_get.return_value = [{"name": "Eiffel Tower", "rating": 4.8}]
        
        resp = client.get('/plan/api/attractions/Paris')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['attractions'][0]['name'] == "Eiffel Tower"

# TESTY DANYCH I PRYWATNOŚCI
def test_save_plan_logged_in(client, new_user):
    """Zalogowany użytkownik może zapisać plan"""
    # Logowanie
    client.post('/login', data={'email': new_user.email, 'password': 'Test1234'})
    
    # Dane planu w formacie JSON
    plan_mock = {
        "query": {"city": "Berlin", "days": 2, "style": "Ekonomiczny"},
        "cost": {"total_pln": 400, "total_local": 100, "currency": "EUR"},
        "weather": {},
        "attractions": [{"name": "Brama Brandenburska"}]
    }
    
    #Symulacja zapisu planu do bazy danych
    resp = client.post('/plan/save_plan', data={
        'plan_data': json.dumps(plan_mock),
        'cards': ['Brama Brandenburska']
    }, follow_redirects=True)
    
    assert resp.status_code == 200
    assert b'Zapisano' in resp.data

def test_api_geocode_with_query(client):
    """Sprawdza poprawne działanie API geokodowania z wpisanym miastem"""
    resp = client.get('/api/geocode?q=Krakow')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert 'lat' in data[0]
        assert 'lon' in data[0]

def test_api_geocode_empty_query(client):
    """Sprawdza działanie API geokodowania z pustym zapytaniem"""
    resp = client.get('/api/geocode')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_cannot_view_others_plan(client, new_user):
    """Użytkownik A nie powinien mieć dostępu do planu użytkownika B"""
    client.post('/login', data={'email': new_user.email, 'password': 'Test1234'})
    
    resp = client.get('/plan/view/999')
    assert resp.status_code in [404, 403] #404 nie istnieje, 403 cudzy plan


#TESTY INTEGRACJI Z SUPABASE 
def test_sync_auth_user_not_found(client):
    """Próba synchronizacji użytkownika, który nie istnieje w bazie danych"""
    payload = {'email': 'nonexistent@test.com', 'supabase_uid': str(uuid.uuid4())}
    resp = client.post('/sync-auth-user', json=payload)
    assert resp.status_code == 404

def test_sync_auth_user_missing_data(client):
    """Próba synchronizacji użytkownika z brakującymi danymi identyfikatora UUID"""
    payload = {'email': 'test@test.com'} # Brak uuid
    resp = client.post('/sync-auth-user', json=payload)
    assert resp.status_code == 400