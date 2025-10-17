from flask import render_template, request, redirect, url_for
from . import main
from .forms import PlanGeneratorForm

@main.route('/', methods=['GET', 'POST'])
def index():
    form = PlanGeneratorForm()
    if form.validate_on_submit():
        # Przekierowujemy dane do widoku, który wygeneruje plan
        city = form.city.data
        days = form.days.data
        style = form.travel_style.data
        return redirect(url_for('plans.show_plan', city=city, days=days, style=style))
    return render_template('index.html', form=form)
