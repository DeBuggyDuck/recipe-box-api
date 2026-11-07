import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class UsersConfig:
    PORT = 5001
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "USERS_DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'users.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.environ.get("JWT_SECRET")