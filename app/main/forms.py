from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class PlanGeneratorForm(FlaskForm):
    city = StringField('Miasto docelowe', validators=[DataRequired()])
    days = IntegerField('Liczba dni', validators=[
        DataRequired(), 
        NumberRange(min=1, max=30, message="Liczba dni musi być pomiędzy 1 a 30.")
    ])
    travel_style = SelectField('Styl podróży', choices=[
        ('Ekonomiczny', 'Ekonomiczny'),
        ('Standardowy', 'Standardowy'),
        ('Komfortowy', 'Komfortowy')
    ], validators=[DataRequired()])
    submit = SubmitField('Generuj Plan')
