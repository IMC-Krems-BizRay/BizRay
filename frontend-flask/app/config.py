from datetime import timedelta
import os

# .../frontend-flask  (one level up from app/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INSTANCE_DIR = os.path.join(PROJECT_ROOT, 'instance')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'site.db')

SECRET_KEY = 'secret-key-abc'
SQLALCHEMY_TRACK_MODIFICATIONS = False

SESSION_PERMANENT = False
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
SESSION_REFRESH_EACH_REQUEST = True


