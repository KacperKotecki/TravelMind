from flask import render_template, request, redirect, url_for, jsonify, current_app, flash
from flask_login import current_user, login_required # Usuń login_user, logout_user (używane w auth)
from . import main
from .forms import PlanGeneratorForm
import json
import os
from app.recommendations import get_grouped_recommendations
from app.utils import build_geocode_variants, normalize_city_name
from app.api import search_city_suggestions 
from app.models import GeneratedPlan # Import User jest tu zbędny, jeśli nie używasz go bezpośrednio w query


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
        # ... (Twoja logika indexu jest OK) ...
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

        if city_input and city_input.strip():
            # ... (logika dla miasta) ...
            normalized_city = normalize_city_name(city_input, destinations)
            
            if normalized_city:
                selected_city_name = normalized_city['name']
                cost_multiplier = normalized_city.get('cost_multiplier', 1.2)
                city_country = normalized_city.get('country') 
            else:
                selected_city_name = city_input.strip()
                cost_multiplier = 1.2
                city_country = None
            
            params = {"cost_mult": cost_multiplier}
            if start_iso: params["start"] = start_iso
            if end_iso: params["end"] = end_iso
            if city_country: params["country"] = city_country
            
            lat = request.form.get("city_lat")
            lon = request.form.get("city_lon")
            if lat: params["lat"] = lat
            if lon: params["lon"] = lon

            return redirect(
                url_for("plans.show_plan", city=selected_city_name, days=days, style=style, **params)
            )
        
        elif vibes_input:
            # ... (logika dla vibes) ...
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
                flash("Niestety nie znaleźliśmy idealnych miast dla wybranych kryteriów.", "warning")
        
        else:
            flash("Musisz wpisać miasto LUB wybrać klimat podróży!", "error")
        
        return render_template("index.html", form=form)
    
    return render_template("index.html", form=form)


@main.route("/api/geocode")
def api_geocode():
    """Proxy dla frontendu do wyszukiwania miast (Autocomplete)."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    
    try:
        variants = build_geocode_variants(q)
        search_q = variants[1] if len(variants) > 1 else variants[0]
    except Exception:
        search_q = q
        
    results = search_city_suggestions(search_q)
    return jsonify(results)


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


@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/contact')
def contact():
    return render_template('contact.html')