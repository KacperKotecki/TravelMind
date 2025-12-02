from flask import abort, jsonify, render_template, request, flash, redirect, url_for
from flask_login import current_user
import json
import os
from datetime import datetime
from . import plans
from ..services import get_plan_details
from ..api_clients import get_attractions


@plans.route("/<string:city>/<int:days>/<string:style>")
def show_plan(city, days, style):
    # Pobierz ewentualne daty z query params (start,end) w formacie YYYY-MM-DD
    start = request.args.get("start")
    end = request.args.get("end")
    # Przytnij nazwę miasta na wypadek przypadkowych spacji/znaków
    if isinstance(city, str):
        city = city.strip()
    # Pobierz współrzędne jeśli przekazano z formularza/autocomplete
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    # Pobierz mnożnik kosztów (domyślnie 1.2 jeśli brak)
    try:
        cost_mult = float(request.args.get("cost_mult", 1.2))
    except (ValueError, TypeError):
        cost_mult = 1.2

    plan_data = get_plan_details(
        city, days, style, start_date=start, end_date=end, lat=lat, lon=lon, cost_mult=cost_mult
    )
    if plan_data.get("error"):
        # Prosta obsługa błędów z serwisu
        abort(404, description=plan_data["error"])
    return render_template("plan_results.html", plan=plan_data)


@plans.route("/api/attractions/<string:city>")
def api_get_attractions(city):
    """API endpoint to fetch attractions for a given city."""
    attractions_data = get_attractions(city, limit=10)  # Użyjmy rozsądnego limitu

    if attractions_data is None:
        # Błąd po stronie serwera lub problem z API Google
        return jsonify({"error": "Nie udało się pobrać danych o atrakcjach."}), 500

    return jsonify({"attractions": attractions_data})


@plans.route("/save_plan", methods=["POST"])
def save_plan():
    plan_json = request.form.get("plan_data")
    if not plan_json:
        flash("Błąd: Brak danych planu do zapisu.", "danger")
        return redirect(request.referrer or url_for('main.index'))
    
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError:
        flash("Błąd: Nieprawidłowe dane planu.", "danger")
        return redirect(request.referrer or url_for('main.index'))

    user_email = current_user.email if current_user.is_authenticated else "Nieznany (niezalogowany)"
    
    # Pobierz zaznaczone atrakcje z formularza
    selected_cards = request.form.getlist('cards')
    
    # Pobierz styl i koszt
    style = plan.get('query', {}).get('style', 'Nieznany')
    total_cost = plan.get('cost', {}).get('total_pln', 'Brak danych')
    
    # Formatowanie danych zgodnie z życzeniem:
    # data | mail uzytkownika | styl | koszt | dane pogodowe na podane dni :{} | Atrakcje {nazwa atrakcji adres, rating, typy }
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Pogoda
    weather_summary = {}
    if 'weather' in plan and isinstance(plan['weather'], dict):
        daily = plan['weather'].get('daily', [])
        if isinstance(daily, list):
            for day in daily:
                date_str = day.get('date', 'N/A')
                desc = day.get('opis', '')
                temp_min = day.get('temperatura_min', '-')
                temp_max = day.get('temperatura_max', '-')
                weather_summary[date_str] = f"{desc} ({temp_min}/{temp_max}°C)"
    
    # Atrakcje
    attractions_summary = []
    if 'attractions' in plan and isinstance(plan['attractions'], list):
        # Jeśli użytkownik zaznaczył jakieś atrakcje, filtrujemy listę
        # Jeśli nie zaznaczył nic (lista selected_cards jest pusta), bierzemy wszystkie
        
        source_attractions = plan['attractions']
        if selected_cards:
            # Filtrujemy po nazwie
            source_attractions = [attr for attr in source_attractions if attr.get('name') in selected_cards]
            
        for attr in source_attractions:
            # Format: {nazwa atrakcji adres, rating, typy }
            name = attr.get('name', 'Brak nazwy')
            address = attr.get('address', 'Brak adresu')
            rating = attr.get('rating', 'N/A')
            types = attr.get('types', [])
            types_str = ", ".join(types) if types else "Brak typów"
            
            attr_str = f"{{nazwa: {name}, adres: {address}, rating: {rating}, typy: {types_str}}}"
            attractions_summary.append(attr_str)
            
    attractions_text = ", ".join(attractions_summary)
    
    line = f"{now} | {user_email} | Styl: {style} | Koszt: {total_cost} PLN | Dane pogodowe: {weather_summary} | Atrakcje: {attractions_text}\n"
    
    # Zapis do pliku saved_plans.txt w głównym katalogu
    try:
        with open("saved_plans.txt", "a", encoding="utf-8") as f:
            f.write(line)
        flash("Plan został pomyślnie zapisany!", "success")
    except Exception as e:
        flash(f"Wystąpił błąd podczas zapisywania pliku: {e}", "danger")
        
    return redirect(request.referrer or url_for('main.index'))


# Dodaj inne trasy
