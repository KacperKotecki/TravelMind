from flask import abort, jsonify, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required
import json
from datetime import datetime
from . import plans
from ..services import get_plan_details
from ..api_clients import get_attractions
from app.models import GeneratedPlan, db

# -------------------------------------------------------------------------
# 1. GENEROWANIE NOWEGO PLANU (Dla niezapisanych)
# -------------------------------------------------------------------------
@plans.route("/<string:city>/<int:days>/<string:style>")
def show_plan(city, days, style):
    # Pobieramy parametry z URL
    start = request.args.get("start")
    end = request.args.get("end")
    country = request.args.get("country")
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    
    if isinstance(city, str):
        city = city.strip()

    try:
        cost_mult = float(request.args.get("cost_mult", 1.2))
    except (ValueError, TypeError):
        cost_mult = 1.2

    # Generujemy plan (pogoda, atrakcje z API)
    plan_data = get_plan_details(
        city, days, style, start_date=start, end_date=end, lat=lat, lon=lon, cost_mult=cost_mult
    )
    
    if plan_data.get("error"):
        abort(404, description=plan_data["error"])
    
    # Przekazujemy kraj, by nie zgubił się przy zapisie
    if country:
        plan_data['query']['country'] = country
    
    # is_saved=False -> Pokazujemy przycisk "Zapisz plan"
    return render_template("plan_results.html", plan=plan_data, is_saved=False)


# -------------------------------------------------------------------------
# 2. PODGLĄD ZAPISANEGO PLANU (Z bazy danych) - TEGO BRAKOWAŁO
# -------------------------------------------------------------------------
@plans.route("/view/<int:plan_id>")
@login_required
def view_saved_plan(plan_id):
    # Pobieramy plan z bazy
    saved_plan = GeneratedPlan.query.get_or_404(plan_id)
    
    # Zabezpieczenie: czy to plan tego użytkownika?
    if saved_plan.user_id != current_user.id:
        abort(403) # Brak dostępu

    # Odtwarzamy strukturę danych dla szablonu
    # W attractions_data są już TYLKO TE atrakcje, które użytkownik wybrał przy zapisie
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

    # is_saved=True -> Ukrywamy przycisk "Zapisz plan", bo już jest zapisany
    return render_template("plan_results.html", plan=plan_data, is_saved=True)


# -------------------------------------------------------------------------
# 3. ZAPISYWANIE PLANU DO BAZY (Logika wyboru atrakcji)
# -------------------------------------------------------------------------
@plans.route("/save_plan", methods=["POST"])
@login_required 
def save_plan():
    # Pobieramy cały JSON planu (ukryte pole w formularzu)
    plan_json = request.form.get("plan_data")
    # Pobieramy listę nazw zaznaczonych kafelków
    selected_cards = request.form.getlist('cards')
    
    if not plan_json:
        flash("Błąd: Brak danych planu do zapisu.", "danger")
        return redirect(request.referrer or url_for('main.index'))
    
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError:
        flash("Błąd: Nieprawidłowe dane planu.", "danger")
        return redirect(request.referrer or url_for('main.index'))

    # --- FILTROWANIE ATRAKCJI ---
    full_attractions_list = plan.get('attractions', [])
    
    # Logika: Jeśli lista 'selected_cards' jest pusta -> zapisz wszystkie.
    # Jeśli zawiera elementy -> zapisz tylko te, które są na liście.
    if not selected_cards:
        selected_attractions_data = full_attractions_list
        flash_msg = "Zapisano cały plan (nie wybrano konkretnych atrakcji)."
    else:
        # Filtrujemy listę słowników, zostawiając te, których 'name' jest w selected_cards
        selected_attractions_data = [
            attr for attr in full_attractions_list 
            if attr.get('name') in selected_cards
        ]
        flash_msg = "Zapisano plan z wybranymi atrakcjami!"

    # Przygotowanie reszty danych
    query = plan.get('query', {})
    cost = plan.get('cost', {})
    
    data_start = None
    data_end = None
    try:
        if query.get('start'):
            data_start = datetime.strptime(query['start'], "%Y-%m-%d").date()
        if query.get('end'):
            data_end = datetime.strptime(query['end'], "%Y-%m-%d").date()
    except ValueError:
        pass 

    try:
        total_cost_pln = float(cost.get('total_pln')) if cost.get('total_pln') is not None else None
    except (ValueError, TypeError):
        total_cost_pln = None
            
    try:
        total_cost_local = float(cost.get('total_local')) if cost.get('total_local') is not None else None
    except (ValueError, TypeError):
        total_cost_local = None

    # Tworzenie obiektu bazy danych
    new_plan = GeneratedPlan(
        city=query.get('city', 'Nieznane'),
        country=query.get('country'),
        days=query.get('days'),
        travel_style=query.get('style'),
        vacation_type=None, 
        data_start=data_start,
        data_end=data_end,
        total_cost_pln=total_cost_pln,
        total_cost_local_currency=total_cost_local,
        local_currency_code=cost.get('currency'),
        weather_data=plan.get('weather'),
        attractions_data=selected_attractions_data, # ZAPISUJEMY PRZEFILTROWANE DANE
        user_id=current_user.id
    )
    
    try:
        db.session.add(new_plan)
        db.session.commit()
        flash(flash_msg, "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Błąd zapisu bazy danych: {e}", "danger")
    
    return redirect(url_for('main.my_plans'))


@plans.route("/api/attractions/<string:city>")
def api_get_attractions(city):
    attractions_data = get_attractions(city, limit=10)
    if attractions_data is None:
        return jsonify({"error": "Nie udało się pobrać danych o atrakcjach."}), 500
    return jsonify({"attractions": attractions_data})