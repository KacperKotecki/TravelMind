from flask import render_template, request, redirect, url_for, jsonify, current_app, flash
from flask_login import login_user, logout_user, current_user, login_required
from . import main
from .forms import PlanGeneratorForm
from ..api_clients import build_geocode_variants
from app.forms import LoginForm, RegistrationForm
from app.models import User, GeneratedPlan
from app import db
from flask_mail import Message
from app import mail
from app.forms import RequestResetForm, ResetPasswordForm

@main.route("/", methods=["GET", "POST"])
def index():
    form = PlanGeneratorForm()
    if form.validate_on_submit():
        # Przekierowujemy dane do widoku, który wygeneruje plan
        city = form.city.data
        if isinstance(city, str):
            city = city.strip()
        start = form.start_date
        end = form.end_date
        style = form.travel_style.data

        # Oblicz liczbę dni na podstawie wybranych dat (włącznie)
        if start and end:
            delta = (end - start).days
            days = delta + 1 if delta >= 0 else 1
        else:
            # fallback na wypadek braku dat — zachowaj krótki domyśl
            days = 3

        # Zapisz plan do bazy, jeśli użytkownik jest zalogowany
        if current_user.is_authenticated:
            plan = GeneratedPlan(
                city=city,
                days=days,
                travel_style=style,
                data_start=start,
                data_end=end,
                user_id=current_user.id
            )
            try:
                db.session.add(plan)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Błąd zapisywania planu: {e}")

        # Dołącz daty jako parametry zapytania, aby widok planów mógł pobrać pogodę dla zakresu
        params = {}
        try:
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()
            # jeśli front-end podał współrzędne (autocomplete), dołącz je
            lat = request.form.get("city_lat")
            lon = request.form.get("city_lon")
            if lat:
                params["lat"] = lat
            if lon:
                params["lon"] = lon
        except Exception:
            # jeśli start/end nie są obiektami daty, pomiń
            pass
        return redirect(
            url_for("plans.show_plan", city=city, days=days, style=style, **params)
        )
    return render_template("index.html", form=form)


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
            flash('Wystąpił błąd podczas rejestracji. Spróbuj ponownie.', 'danger')
    
    return render_template("register.html", form=form)
@main.route('/logout')
def logout():
    logout_user()
    flash('Zostałeś wylogowany.', 'info')
    return redirect(url_for('main.login'))

@main.route('/account')
@login_required
def account():
    return render_template('account.html')

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