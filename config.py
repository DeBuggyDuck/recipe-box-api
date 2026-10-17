import os

class Config:
    DEBUG = False
    TESTING = False
    DATABASE = os.environ.get("DATABASE_URL", "recipes.db")

    JWT_SECRET = os.environ.get("JWT_SECRET")
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is required but not set in the environment")

class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE = "recipes_test.db"


class ProductionConfig(Config):
    pass