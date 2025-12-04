from flask import render_template, request, redirect, url_for, jsonify, current_app, flash
from flask_login import login_user, logout_user, current_user, login_required
from . import main
from .forms import PlanGeneratorForm
from ..api_clients import build_geocode_variants
from app.forms import LoginForm 
import json
import os
from app.utils import normalize_city_name
from app.recommendations import recommend_city, get_grouped_recommendations


from app.models import User, GeneratedPlan
from app import db, mail
from flask_mail import Message
from app.forms import  RegistrationForm, RequestResetForm, ResetPasswordForm

# Krok 5: Przygotowanie stałych finansowych
# Bazowe koszty dzienne w PLN dla różnych stylów podróży (mnożnik 1.0)
BASE_COSTS = {
    "Ekonomiczny": 250,   # np. hostel, tanie jedzenie, darmowe atrakcje
    "Standardowy": 500,   # np. hotel 3*, restauracje, płatne bilety
    "Komfortowy": 1000    # np. hotel 4-5*, taxi, drogie atrakcje
}

def load_destinations():
    """Ładuje listę miast z pliku JSON."""
    try:
        json_path = os.path.join(current_app.root_path, 'plans', 'destinations.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        current_app.logger.error(f"Błąd ładowania destinations.json: {e}")
        return []

@main.route("/", methods=["GET", "POST"])
def index():
    form = PlanGeneratorForm()
    if form.validate_on_submit():
        city_input = form.city.data
        vibes_input = form.vibes.data
        style = form.travel_style.data
        
        destinations = load_destinations()
        
        start = form.start_date
        end = form.end_date
        
        if start and end:
            delta = (end - start).days
            days = delta + 1 if delta >= 0 else 1
        else:
            days = 3
            
        start_iso = start.isoformat() if start else None
        end_iso = end.isoformat() if end else None

        # Ścieżka A: Użytkownik wpisał miasto
        if city_input and city_input.strip():
            normalized_city = normalize_city_name(city_input, destinations)
            
            # Wprowadzamy zmienne dla nazwy miasta i kraju
            if normalized_city:
                selected_city_name = normalized_city['name']
                cost_multiplier = normalized_city.get('cost_multiplier', 1.2)
                city_country = normalized_city.get('country') # <--- Pobieramy kraj
            else:
                selected_city_name = city_input.strip()
                cost_multiplier = 1.2
                city_country = None
            
            # --- USUNIĘTO BLOK AUTOMATYCZNEGO ZAPISU DO BAZY DANYCH ---
            
            params = {"cost_mult": cost_multiplier}
            if start_iso: params["start"] = start_iso
            if end_iso: params["end"] = end_iso
            # --- Dodajemy country do parametrów URL ---
            if city_country: params["country"] = city_country
            
            lat = request.form.get("city_lat")
            lon = request.form.get("city_lon")
            if lat: params["lat"] = lat
            if lon: params["lon"] = lon

            return redirect(
                url_for("plans.show_plan", city=selected_city_name, days=days, style=style, **params)
            )
        
        # Ścieżka B: Użytkownik wybrał kafelki (i NIE wpisał miasta) -> SUGESTIE
        elif vibes_input:
            grouped_suggestions = get_grouped_recommendations(vibes_input, destinations, budget_style=style)
            
            if grouped_suggestions:
                return render_template(
                    "suggestions.html",
                    grouped_suggestions=grouped_suggestions,
                    vibes=vibes_input,
                    days=days,
                    style=style,
                    start_date=start_iso,
                    end_date=end_iso
                )
            else:
                flash("Niestety nie znaleźliśmy idealnych miast dla wybranych kryteriów. Spróbuj zmienić filtry.", "warning")
        
        # Walidacja: Ani miasto, ani kafelki nie wybrane
        else:
            flash("Musisz wpisać miasto LUB wybrać klimat podróży!", "error")
        
        return render_template("index.html", form=form)
    
    return render_template("index.html", form=form)
# ...existing code...

@main.route("/api/geocode")
def api_geocode():
    """Prosty proxy do Open-Meteo Geocoding API (darmowe). Zwraca listę sugestii.
    Query param: q (string)
    """
    q = request.args.get("q", "")
    q = q.strip()
    if not q:
        return jsonify([])

    # Upraszczamy zapytanie dla lepszych wyników geokodowania - użyjemy zwykle tylko nazwy miasta
    try:
        variants = build_geocode_variants(q)
        # wybierz drugi wariant (zwykle sama nazwa miasta) jeśli istnieje, inaczej pierwszy
        search_q = variants[1] if len(variants) > 1 else variants[0]
    except Exception:
        search_q = q
    try:
        import requests

        om_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": search_q, "count": 6, "language": "pl"}
        resp = requests.get(om_url, params=params, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for r in data.get("results", []):
            name = r.get("name") or ""
            admin1 = r.get("admin1") or ""
            country = r.get("country") or ""
            display = name
            if admin1:
                display += f", {admin1}"
            if country:
                display += f", {country}"
            results.append(
                {"name": display, "lat": r.get("latitude"), "lon": r.get("longitude")}
            )
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Błąd geokodowania (Open-Meteo) dla q={q}: {e}")
        return jsonify([]), 500

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Nieprawidłowy email lub hasło.', 'danger')
            return redirect(url_for('main.login'))
        
        login_user(user)
        
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.index'))
    
    return render_template("login.html", form=form)


# ...existing code...
@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data.lower()
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Konto zostało utworzone! Możesz się teraz zalogować.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            # Log full stacktrace to log file and console
            current_app.logger.exception("Registration error")
            # In development show the error message to help debugging
            flash(f'Wystąpił błąd podczas rejestracji: {e}', 'danger')
    
    return render_template("register.html", form=form)
# ...existing code...
@main.route('/logout')
def logout():
    logout_user()
    flash('Zostałeś wylogowany.', 'info')
    return redirect(url_for('main.login'))
@main.route('/sync-auth-user', methods=['POST'])
def sync_auth_user():
    """
    Oczekuje JSON: { "email": "user@example.com", "supabase_uid": "uuid-string" }
    Znajduje lokalnego usera po email i ustawia auth_uuid = supabase_uid.
    Zwraca 200 OK lub odpowiedni błąd.
    """
    data = request.get_json() or {}
    email = data.get('email')
    supabase_uid = data.get('supabase_uid')
    if not email or not supabase_uid:
        return jsonify({"error": "email and supabase_uid required"}), 400

    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        return jsonify({"error": "user not found"}), 404

    user.auth_uuid = supabase_uid
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to set auth_uuid: {e}")
        return jsonify({"error": "db error"}), 500

    return jsonify({"status": "ok"}), 200
@main.route('/account')
@login_required
def account():
    return render_template('account.html')

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@main.route('/my-plans')
@login_required
def my_plans():
    user_plans = GeneratedPlan.query.filter_by(user_id=current_user.id).order_by(GeneratedPlan.created_at.desc()).all()
    return render_template('my_plans.html', plans=user_plans)

@main.route('/reset-password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.get_reset_token()
            msg = Message('Reset hasła - TravelMind',
                          recipients=[user.email])
            msg.body = f'''Aby zresetować hasło, kliknij w poniższy link:
{url_for('main.reset_token', token=token, _external=True)}

Jeśli nie prosiłeś o reset hasła, zignoruj tę wiadomość.

Link jest ważny przez 30 minut.
'''
            mail.send(msg)
        
        flash('Jeśli konto z tym emailem istnieje, link resetujący został wysłany.', 'info')
        return redirect(url_for('main.login'))
    
    return render_template('reset_request.html', form=form)

@main.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = User.verify_reset_token(token)
    if user is None:
        flash('Link jest nieprawidłowy lub wygasł.', 'danger')
        return redirect(url_for('main.reset_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Twoje hasło zostało zmienione! Możesz się teraz zalogować.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('reset_token.html', form=form)