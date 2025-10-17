from flask import Blueprint
plans = Blueprint('plans', __name__)
from . import routes
