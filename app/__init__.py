from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config

db = SQLAlchemy()

def create_app(config_name: str):
    """
    Application factory function.
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Inicjalizacja rozszerzeń
    db.init_app(app)
    
    # Rejestracja Blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .plans import plans as plans_blueprint
    app.register_blueprint(plans_blueprint, url_prefix='/plan')
    
    # Import modeli, aby były widoczne dla SQLAlchemy
    from . import models

    return app
