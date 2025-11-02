from flask import render_template, request, redirect, url_for
from . import main
from .forms import PlanGeneratorForm

@main.route('/', methods=['GET', 'POST'])
def index():
    form = PlanGeneratorForm()
    if form.validate_on_submit():
        # Przekierowujemy dane do widoku, który wygeneruje plan
        city = form.city.data
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
        except Exception:
            # jeśli start/end nie są obiektami daty, pomiń
            pass
        return redirect(url_for('plans.show_plan', city=city, days=days, style=style, **params))
    return render_template('index.html', form=form)
