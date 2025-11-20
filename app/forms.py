from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    submit = SubmitField('Zaloguj się')

class RegistrationForm(FlaskForm):
    first_name = StringField('Imię', validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField('Nazwisko', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Numer telefonu', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Powtórz hasło', validators=[
        DataRequired(), 
        EqualTo('password', message='Hasła muszą być identyczne')
    ])
    submit = SubmitField('Zarejestruj się')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Ten adres email jest już zarejestrowany.')