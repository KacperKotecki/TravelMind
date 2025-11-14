from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, ValidationError
from wtforms.validators import DataRequired
from datetime import datetime


class PlanGeneratorForm(FlaskForm):
    city = StringField("Miasto docelowe", validators=[DataRequired()])
    date_range = StringField(
        "Zakres dat", validators=[DataRequired(message="Proszę wybrać zakres dat.")]
    )

    def validate_date_range(self, field):
        """
        Waliduje pole date_range. Oczekuje formatu 'YYYY-MM-DD - YYYY-MM-DD'.
        Sprawdza poprawność dat, kolejność i maksymalny dozwolony przedział.
        Po pomyślnej walidacji zapisuje daty w self.start_date i self.end_date.
        """
        try:
            parts = field.data.split(" - ")
            if len(parts) != 2:
                raise ValueError("Nieprawidłowy format zakresu dat.")

            start_str, end_str = parts
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()

            if end_date < start_date:
                raise ValidationError(
                    "Data powrotu nie może być wcześniejsza niż data wyjazdu."
                )

            delta_days = (end_date - start_date).days + 1
            if delta_days > 14:
                raise ValidationError("Maksymalny dozwolony przedział to 14 dni.")

            # Zapisz przetworzone daty w formularzu do późniejszego wykorzystania w trasie
            self.start_date = start_date
            self.end_date = end_date

        except (ValueError, ValidationError) as e:
            # Jeśli błąd walidacji, rzuć go dalej
            if isinstance(e, ValidationError):
                raise e
            # Jeśli błąd parsowania, rzuć generyczny błąd
            raise ValidationError(
                "Nieprawidłowy format dat. Użyj kalendarza do wyboru zakresu."
            )

    travel_style = SelectField(
        "Styl podróży",
        choices=[
            ("Ekonomiczny", "Ekonomiczny"),
            ("Standardowy", "Standardowy"),
            ("Komfortowy", "Komfortowy"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Generuj Plan")
