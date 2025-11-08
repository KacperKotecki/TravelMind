from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_migrate import Migrate
import logging
from flask_login import LoginManager
from .models import User

db = SQLAlchemy()
login_manager = LoginManager()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Zaloguj się, aby uzyskać dostęp do tej strony.'

@login_manager.user_loader
def load_user(user_id):
    """Funkcja wczytuje użytkownika na podstawie jego ID"""
    return User.query.get(int(user_id))

def create_app(config_name: str):
    """
    Application factory function.
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Konfiguracja logowania
    if app.config['DEBUG']:
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)

    # Inicjalizacja rozszerzeń
    db.init_app(app)
    migrate = Migrate(app, db)
    # Rejestracja Blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .plans import plans as plans_blueprint
    app.register_blueprint(plans_blueprint, url_prefix='/plan')

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    # Import modeli, aby były widoczne dla SQLAlchemy
    from . import models

    return app
