import os
from dotenv import load_dotenv

# Wskazanie ścieżki do pliku .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class BaseConfig:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-hard-to-guess-string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API Keys
    OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
    GEOAPIFY_API_KEY = os.environ.get('GEOAPIFY_API_KEY')
    GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')

    #Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@travelmind.com')


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    # Jeśli DEV_DATABASE_URL jest ustawiony w .env, używaj PostgreSQL
    # W przeciwnym razie powróć do SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir,'app-dev.db')


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    # DATABASE_URL powinien być ustawiony w zmiennych środowiskowych przy deployu
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://localhost/travelmind')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}