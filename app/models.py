from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db # Zostanie zaimportowane w kolejnym kroku



class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    generated_plans = db.relationship('GeneratedPlan', backref='user', lazy=True)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'
class GeneratedPlan(db.Model):
    __tablename__ = 'generated_plans'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100))
    days = db.Column(db.Integer, nullable=False)
    travel_style = db.Column(db.String(50), nullable=False)
    vacation_type = db.Column(db.String(50))
    data_start = db.Column(db.Date)
    data_end = db.Column(db.Date)
    
    total_cost_pln = db.Column(db.Float)
    total_cost_local_currency = db.Column(db.Float)
    local_currency_code = db.Column(db.String(3))

    weather_data = db.Column(db.JSON) #dane z open-meteo
    attractions_data = db.Column(db.JSON) #dane z google places

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __repr__(self):
        return f'<GeneratedPlan for {self.city} ({self.days} days)>'
