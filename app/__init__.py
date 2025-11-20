from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
from flask_migrate import Migrate
import logging

db = SQLAlchemy()
login_manager = LoginManager()

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
    
    # Inicjalizacja Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Zaloguj się, aby uzyskać dostęp do tej strony.'
    login_manager.login_message_category = 'info'
    
    # Import modeli, aby były widoczne dla SQLAlchemy
    from . import models
    
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))
    
    # Rejestracja Blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .plans import plans as plans_blueprint
    app.register_blueprint(plans_blueprint, url_prefix='/plan')

    return app