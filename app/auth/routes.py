from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db, mail
from app.models import User
from . import auth
from .forms import LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm
from flask_mail import Message

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash('Nieprawidłowy email lub hasło.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.index'))
    
    return render_template("login.html", form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data.lower()
        )
        if hasattr(form, 'phone'): # Jeśli używasz pola phone
             # user.phone = form.phone.data  # Dodaj pole w modelu User jeśli potrzebne
             pass

        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Konto zostało utworzone! Możesz się teraz zalogować.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Wystąpił błąd: {e}', 'danger')
    
    return render_template("register.html", form=form)

@auth.route('/logout')
def logout():
    logout_user()
    flash('Zostałeś wylogowany.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.get_reset_token()
            msg = Message('Reset hasła - TravelMind',
                          recipients=[user.email])
            # Uwaga: url_for('auth.reset_token', ...)
            msg.body = f'''Aby zresetować hasło, kliknij w poniższy link:
{url_for('auth.reset_token', token=token, _external=True)}

Jeśli nie prosiłeś o reset hasła, zignoruj tę wiadomość.
'''
            mail.send(msg)
        flash('Jeśli konto z tym emailem istnieje, link resetujący został wysłany.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_request.html', form=form)

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = User.verify_reset_token(token)
    if user is None:
        flash('Link jest nieprawidłowy lub wygasł.', 'danger')
        return redirect(url_for('auth.reset_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Twoje hasło zostało zmienione! Możesz się teraz zalogować.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_token.html', form=form)