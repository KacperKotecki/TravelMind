from os import getenv
from app import create_app, db
from app.models import User

config = getenv('FLASK_CONFIG') or getenv('FLASK_ENV') or 'development'
app = create_app(config)

with app.app_context():
    u = User(first_name=None, last_name=None, email='test+dev@example.com')
    u.set_password('Test1234')
    db.session.add(u)
    try:
        db.session.commit()
        print('OK, created user id', u.id)
    except Exception as e:
        db.session.rollback()
        print('Error:', repr(e))