import os
from flask import Flask, session
from .models import db, bcrypt
from flask_migrate import Migrate

migrate = Migrate()

def create_app():
    # point Flask at the existing instance/ outside the package
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    instance_dir = os.path.join(project_root, 'instance')

    app = Flask(__name__, instance_path=instance_dir)

    from . import config as app_config
    app.config.from_object(app_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    from .routes import main
    app.register_blueprint(main)

    @app.context_processor
    def inject_logged_in():
        return {"logged_in": session.get("logged_in")}

    return app

