from app import create_app, db
from app.models import User, GeneratedPlan

app = create_app('default')
app.app_context().push()

# 🧹 Czyszczenie bazy przed testem
GeneratedPlan.query.delete()
User.query.delete()
db.session.commit()

# 1️⃣ Dodaj użytkownika
user = User(
    first_name="Emil",
    last_name="G.",
    email="emil@example.com",
    password_hash="hashed_password_123"
)
db.session.add(user)
db.session.commit()
print(f"✅ Dodano użytkownika: {user.email}")

# 2️⃣ Dodaj plan podróży
plan = GeneratedPlan(
    city="Berlin",
    country="Germany",
    days=5,
    travel_style="sightseeing",
    total_cost_pln=2500.0,
    total_cost_local_currency=550.0,  # ✅ poprawiona nazwa
    local_currency_code="EUR",
    user_id=user.id
)
db.session.add(plan)
db.session.commit()
print(f"✅ Dodano plan podróży dla {user.email}: {plan.city}")

# 3️⃣ Sprawdzenie relacji
user_from_db = User.query.filter_by(email="emil@example.com").first()
print("📘 Użytkownik z bazy:", user_from_db)
print("📗 Jego plany podróży:", user_from_db.generated_plans)
