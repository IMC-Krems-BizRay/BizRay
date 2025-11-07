from flask.cli import with_appcontext
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
