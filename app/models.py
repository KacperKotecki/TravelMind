from datetime import datetime
from . import db # Zostanie zaimportowane w kolejnym kroku

class GeneratedPlan(db.Model):
    __tablename__ = 'generated_plans'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100))
    days = db.Column(db.Integer, nullable=False)
    travel_style = db.Column(db.String(50), nullable=False)
    
    total_cost_pln = db.Column(db.Float)
    total_cost_local_currency = db.Column(db.Float)
    local_currency_code = db.Column(db.String(3))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # W przyszłości, po dodaniu użytkowników:
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def __repr__(self):
        return f'<GeneratedPlan for {self.city} ({self.days} days)>'
