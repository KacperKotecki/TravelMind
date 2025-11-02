from app import create_app, db
from app.models import GeneratedPlan, User

app = create_app('default')
with app.app_context():
    user = User.query.first()
    plan = GeneratedPlan(
        city="Barcelona",
        country="Spain",
        days=5,
        travel_style="relax",
        vacation_type="beach",  # ✅ nowe pole
        total_cost_pln=2500,
        local_currency_code="EUR",
        user_id=user.id
    )
    db.session.add(plan)
    db.session.commit()
    print("✅ Plan z vacation_type zapisany poprawnie!")
