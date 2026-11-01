import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    DEBUG = False
    TESTING = False
    DATABASE = os.environ.get("DATABASE_URL", "recipes.db")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'recipes.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.environ.get("JWT_SECRET")

    # Flask-Caching
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 30

    # Flask-Limiter
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = "200 per day;50 per hour"

    # Slow Service URL:
    SLOW_SERVICE_URL = os.environ.get(
        "SLOW_SERVICE_URL", "http://127.0.0.1:5001"
    )


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE = "recipes_test.db"
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{os.path.join(BASE_DIR, 'recipes_test.db')}"
    )
    CACHE_TYPE = "NullCache"
    RATELIMIT_ENABLED = True


class ProductionConfig(Config):
    pass