from datetime import timedelta

SECRET_KEY = 'secret-key-abc'  # use a long, random one in production
SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Session behavior
SESSION_PERMANENT = False
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
SESSION_REFRESH_EACH_REQUEST = True

