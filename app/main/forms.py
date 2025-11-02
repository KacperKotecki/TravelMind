from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, ValidationError
from wtforms.fields import DateField
from wtforms.validators import DataRequired

class PlanGeneratorForm(FlaskForm):
    city = StringField('Miasto docelowe', validators=[DataRequired()])
    start_date = DateField('Data wyjazdu', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Data powrotu', format='%Y-%m-%d', validators=[DataRequired()])
    
    def validate_end_date(self, field):
        """Ensure end_date is not before start_date and the inclusive range is at most 16 days."""
        start = self.start_date.data
        end = field.data
        if start and end:
            if end < start:
                raise ValidationError('Data powrotu nie może być wcześniejsza niż data wyjazdu.')
            # inclusive days
            delta_days = (end - start).days + 1
            if delta_days > 16:
                raise ValidationError('Maksymalny dozwolony przedział to 16 dni.')
    travel_style = SelectField('Styl podróży', choices=[
        ('Ekonomiczny', 'Ekonomiczny'),
        ('Standardowy', 'Standardowy'),
        ('Komfortowy', 'Komfortowy')
    ], validators=[DataRequired()])
    submit = SubmitField('Generuj Plan')
