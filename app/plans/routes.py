from flask import abort, jsonify, render_template, request
from . import plans
from ..services import get_plan_details
from ..api_clients import get_attractions

from .. import db
from ..models import GeneratedPlan
from flask_login import login_required, current_user
from datetime import date


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
    plan_data = get_plan_details(
        city, days, style, start_date=start, end_date=end, lat=lat, lon=lon
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


# Endpoint do zapisywania planu
@plans.route("/save", methods=['POST'])
@login_required
def save_plan():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Brak danych JSON."}), 400

    # pobranie kluczowych danych z obiektu 'plan'
    query_data = data.get('query', {})
    cost_data = data.get('cost', {})
    weather_data = data.get('weather', {})
    # Atrakcje są ładowane przez JS, założenie że frontend dołączy je do obiektu 'data' przed wysłaniem
    attractions_data = data.get('attractions', [])
    city = query_data.get('city')
    days = query_data.get('days')
    style = query_data.get('style')

    if not city or days is None or not style:
        return jsonify({"status": "error", "message": "Brak wymaganych danych: miasto, dni, styl."}), 400


    start_date_obj = None
    if query_data.get('start'):
        try:
            start_date_obj = date.fromisoformat(query_data['start'])
        except (ValueError, TypeError):
            pass

    try:
        new_plan = GeneratedPlan(
            city=city,
            days=int(days),
            travel_style=style,
            data_start=start_date_obj,
            data_end=end_date_obj,
            total_cost_pln=cost_data.get('total_pln'),
            total_cost_local_currency=cost_data.get('total_local'),
            local_currency_code=cost_data.get('currency'),
            weather_data=weather_data,
            attractions_data=attractions_data,
            user=current_user
        )

        db.session.add(new_plan)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Wystąpił błąd serwera podczas zapisu: {str(e)}"}), 500

    return jsonify({
        "status": "success",
        "message": "Plan został pomyślnie zapisany.",
        "plan_id": new_plan.id
    }), 201