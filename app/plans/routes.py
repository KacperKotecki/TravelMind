from flask import session, flash, redirect, url_for, request, render_template, abort, jsonify
from flask_login import current_user, login_required
from datetime import datetime
from . import plans
from ..services import get_plan_details
from app.api import get_attractions
from app.models import GeneratedPlan, db, Country

# -------------------------------------------------------------------------
# 1. GENEROWANIE NOWEGO PLANU (Dla niezapisanych)
# -------------------------------------------------------------------------
@plans.route("/<string:city>/<int:days>/<string:style>")
def show_plan(city, days, style):
    start = request.args.get("start")
    end = request.args.get("end")
    country_name = request.args.get("country")
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    
    if isinstance(city, str):
        city = city.strip()

    try:
        cost_mult = float(request.args.get("cost_mult", 1.2))
    except (ValueError, TypeError):
        cost_mult = 1.2

    # Pobieramy dane planu z serwisu
    plan_data = get_plan_details(
        city, days, style, country=country_name, start_date=start, end_date=end, lat=lat, lon=lon, cost_mult=cost_mult
    )
    
    if plan_data.get("error"):
        abort(404, description=plan_data["error"])
    
    if country_name:
        plan_data['query']['country'] = country_name
        
        # SPRAWDZANIE BEZPIECZEŃSTWA
        country_obj = Country.query.filter_by(name=country_name).first()
        if country_obj and country_obj.danger:
            plan_data['is_dangerous'] = True

    # --- KLUCZOWA POPRAWKA: Zapisz wygenerowany plan do sesji, aby save_plan mógł go odczytać ---
    # Używamy sesji jako bezpiecznego bufora między wyświetleniem a zapisem
    session['current_generated_plan'] = plan_data

    return render_template("plan_results.html", plan=plan_data, is_saved=False)


# -------------------------------------------------------------------------
# 2. PODGLĄD ZAPISANEGO PLANU (Z bazy danych)
# -------------------------------------------------------------------------
@plans.route("/view/<int:plan_id>")
@login_required
def view_saved_plan(plan_id):
    # Pobieramy plan z bazy
    saved_plan = GeneratedPlan.query.get_or_404(plan_id)
    
    # Zabezpieczenie: czy to plan tego użytkownika?
    if saved_plan.user_id != current_user.id:
        abort(403) # Brak dostępu

    # Odtwarzamy strukturę danych dla szablonu (mapowanie z modelu DB na obiekt dla widoku)
    plan_data = {
        "query": {
            "city": saved_plan.city,
            "days": saved_plan.days,
            "style": saved_plan.travel_style,
            "country": saved_plan.country,
            "start": saved_plan.data_start.isoformat() if saved_plan.data_start else None,
            "end": saved_plan.data_end.isoformat() if saved_plan.data_end else None
        },
        "cost": {
            "total_pln": saved_plan.total_cost_pln,
            "total_local": saved_plan.total_cost_local_currency,
            "currency": saved_plan.local_currency_code
        },
        "weather": saved_plan.weather_data or {},
        "attractions": saved_plan.attractions_data or [] 
    }

    return render_template("plan_results.html", plan=plan_data, is_saved=True)


@plans.route("/api/attractions/<string:city>")
def api_get_attractions(city):
    country = request.args.get("country")
    attractions_data = get_attractions(city, country=country, limit=10)
    
    if attractions_data is None:
        return jsonify({"error": "Nie udało się pobrać danych o atrakcjach."}), 500
    return jsonify({"attractions": attractions_data})


# -------------------------------------------------------------------------
# 3. ZAPISYWANIE PLANU DO BAZY
# -------------------------------------------------------------------------
@plans.route('/save_plan', methods=['POST'])
@login_required
def save_plan():
    # 1. Pobierz dane z sesji server-side (zamiast z formularza HTML)
    plan_data = session.get('current_generated_plan')

    if not plan_data:
        flash("Twoja sesja wygasła lub plan nie został znaleziony. Wygeneruj plan ponownie.", "danger")
        return redirect(url_for('main.index'))

    # 2. Parsowanie dat z powrotem do obiektów date (bo JSON w sesji przechowuje je jako stringi)
    # Zakładamy format ISO YYYY-MM-DD
    try:
        start_str = plan_data['query'].get('start')
        end_str = plan_data['query'].get('end')
        
        d_start = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else None
        d_end = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
    except ValueError:
        d_start = None
        d_end = None

    # 3. Utwórz obiekt GeneratedPlan (zgodny z Twoim model.py)
    new_plan = GeneratedPlan(
        user_id=current_user.id,
        city=plan_data['query']['city'],
        country=plan_data['query'].get('country'),
        days=plan_data['query']['days'],
        travel_style=plan_data['query']['style'],
        
        data_start=d_start,
        data_end=d_end,
        
        total_cost_pln=plan_data['cost'].get('total_pln'),
        total_cost_local_currency=plan_data['cost'].get('total_local'),
        local_currency_code=plan_data['cost'].get('currency'),
        
        weather_data=plan_data.get('weather'),
        attractions_data=plan_data.get('attractions')
    )

    try:
        db.session.add(new_plan)
        db.session.commit()
        
        # 4. Czyścimy plan z sesji po udanym zapisie
        session.pop('current_generated_plan', None)
        
        # Przekierowujemy do listy planów użytkownika po zapisie
        flash("Twój plan podróży został pomyślnie zapisany!", "success")
        return redirect(url_for('main.my_plans'))
        
    except Exception as e:
        db.session.rollback()
        # Logowanie błędu warto dodać w przyszłości np. current_app.logger.error(str(e))
        flash(f"Wystąpił błąd bazy danych podczas zapisywania: {str(e)}", "danger")
        return redirect(url_for('main.index'))