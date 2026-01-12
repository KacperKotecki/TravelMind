from flask import Blueprint
main = Blueprint('main', __name__)
from app.constants import TAG_TRANSLATIONS
from . import routes
from flask import Blueprint

@main.app_template_filter('translate_tag')
def translate_tag_filter(tag_key):
    return TAG_TRANSLATIONS.get(tag_key, tag_key)
