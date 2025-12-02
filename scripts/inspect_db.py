from os import getenv
from app import create_app, db
from sqlalchemy import inspect

# wybierz konfigurację (z env lub 'development')
config = getenv('FLASK_CONFIG') or getenv('FLASK_ENV') or 'development'
app = create_app(config)

with app.app_context():
    print("CONFIG:", config)
    print("SQLALCHEMY_DATABASE_URI:", app.config.get('SQLALCHEMY_DATABASE_URI'))
    insp = inspect(db.engine)
    tables = insp.get_table_names()
    print("Tables:", tables)
    if 'users' in tables:
        cols = insp.get_columns('users')
        for c in cols:
            print(c['name'], 'nullable=', c.get('nullable'), 'type=', c.get('type'))
    else:
        print("Table 'users' not found")