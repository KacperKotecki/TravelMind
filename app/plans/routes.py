from flask import render_template, abort, request
from . import plans
from ..services import get_plan_details

@plans.route('/<string:city>/<int:days>/<string:style>')
def show_plan(city, days, style):
    # Pobierz ewentualne daty z query params (start,end) w formacie YYYY-MM-DD
    start = request.args.get('start')
    end = request.args.get('end')
    # Przytnij nazwę miasta na wypadek przypadkowych spacji/znaków
    if isinstance(city, str):
        city = city.strip()
    # Pobierz współrzędne jeśli przekazano z formularza/autocomplete
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    plan_data = get_plan_details(city, days, style, start_date=start, end_date=end, lat=lat, lon=lon)
    if plan_data.get("error"):
        # Prosta obsługa błędów z serwisu
        abort(404, description=plan_data["error"])
    return render_template('plan_results.html', plan=plan_data)
