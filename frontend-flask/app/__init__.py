import os
from flask import Flask, session, request
from datetime import timedelta  
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

    # 🔹 enable long-term caching for static files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=365)
    
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    from .routes import main
    app.register_blueprint(main)

    @app.context_processor
    def inject_logged_in():
        return {"logged_in": session.get("logged_in")}


    @app.after_request
    def add_cache_headers(response):
        """
        Cache static public pages, but do NOT cache auth pages.
        """

        # If the route already has specific cache headers, don't override it
        if 'Cache-Control' in response.headers:
            return response

        endpoint = request.endpoint or ""

        # Pages safe to cache for 5 minutes
        cacheable = {
            "main.index",
            "main.search_results",
            "main.view_company",
        }

        # GET requests only
        if request.method == "GET" and endpoint in cacheable:
            response.cache_control.public = True
            response.cache_control.max_age = 300  # 5 minutes
        else:
            # Do NOT cache login, register, logout, POST, etc.
            response.headers['Cache-Control'] = 'no-store'

        return response


    return app

