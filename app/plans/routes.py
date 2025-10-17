from flask import render_template, abort
from . import plans
from ..services import get_plan_details

@plans.route('/<string:city>/<int:days>/<string:style>')
def show_plan(city, days, style):
    plan_data = get_plan_details(city, days, style)
    if plan_data.get("error"):
        # Prosta obsługa błędów z serwisu
        abort(404, description=plan_data["error"])
    return render_template('plan_results.html', plan=plan_data)
