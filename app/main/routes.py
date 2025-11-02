from flask import render_template, request, redirect, url_for, jsonify, current_app
from . import main
from .forms import PlanGeneratorForm

@main.route('/', methods=['GET', 'POST'])
def index():
    form = PlanGeneratorForm()
    if form.validate_on_submit():
        # Przekierowujemy dane do widoku, który wygeneruje plan
        city = form.city.data
        if isinstance(city, str):
            city = city.strip()
        start = form.start_date.data
        end = form.end_date.data
        style = form.travel_style.data

        # Oblicz liczbę dni na podstawie wybranych dat (włącznie)
        if start and end:
            delta = (end - start).days
            days = delta + 1 if delta >= 0 else 1
        else:
            # fallback na wypadek braku dat — zachowaj krótki domyśl
            days = 3

        # Dołącz daty jako parametry zapytania, aby widok planów mógł pobrać pogodę dla zakresu
        params = {}
        try:
            if start:
                params['start'] = start.isoformat()
            if end:
                params['end'] = end.isoformat()
            # jeśli front-end podał współrzędne (autocomplete), dołącz je
            lat = request.form.get('city_lat')
            lon = request.form.get('city_lon')
            if lat:
                params['lat'] = lat
            if lon:
                params['lon'] = lon
        except Exception:
            # jeśli start/end nie są obiektami daty, pomiń
            pass
        return redirect(url_for('plans.show_plan', city=city, days=days, style=style, **params))
    return render_template('index.html', form=form)


@main.route('/api/geocode')
def api_geocode():
    """Prosty proxy do Open-Meteo Geocoding API (darmowe). Zwraca listę sugestii.
    Query param: q (string)
    """
    q = request.args.get('q', '')
    q = q.strip()
    if not q:
        return jsonify([])
    try:
        import requests
        om_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": q, "count": 6, "language": "pl"}
        resp = requests.get(om_url, params=params, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for r in data.get('results', []):
            name = r.get('name') or ''
            admin1 = r.get('admin1') or ''
            country = r.get('country') or ''
            display = name
            if admin1:
                display += f", {admin1}"
            if country:
                display += f", {country}"
            results.append({"name": display, "lat": r.get('latitude'), "lon": r.get('longitude')})
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Błąd geokodowania (Open-Meteo) dla q={q}: {e}")
        return jsonify([]), 500
