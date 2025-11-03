from flask import abort, jsonify, render_template, request
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


# Dodaj inne trasy
