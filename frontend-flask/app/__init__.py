from flask import Flask, session
from .models import db, bcrypt
from flask_migrate import Migrate

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    from . import config as app_config
    app.config.from_object(app_config)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    from .routes import main
    app.register_blueprint(main)

    @app.context_processor
    def inject_logged_in():
        return {"logged_in": session.get("logged_in")}

    return app

