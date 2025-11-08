from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import auth
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User
from app import db


# Rejestracja użytkowników
@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Obsługuje rejestrację nowych użytkowników"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data
        )

        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash('Rejestracja zakończona sukcesem! Możesz się teraz zalogować.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Rejstracja', form=form)


# Loowanie użytkowników
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Obsługuje logowanie użytkowników"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Nieprawidłowy email lub hasło.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.index'))
    
    return render_template('auth/login.html', title='Logowanie', form=form)


# Wylogowywanie użytkowników
@auth.route('/logout')
def logout():
    """Obsługuje wylogowywanie użytkowników"""
    logout_user()
    flash('Wylogowano pomyślnie.', 'success')
    return redirect(url_for('main.index'))