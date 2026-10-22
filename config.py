import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    DEBUG = False
    TESTING = False
    DATABASE = os.environ.get("DATABASE_URL", "recipes.db")
    
    # PUT IT HERE:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'recipes.db')}"
    )
    JWT_SECRET = os.environ.get("JWT_SECRET")


class DevelopmentConfig(Config):
    DEBUG = True
    # If you put it in Config above, you don't even need it here!
    # Or, if you prefer overriding it specifically for dev, you can put it here.


class TestingConfig(Config):
    TESTING = True
    DATABASE = "recipes_test.db"
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{os.path.join(BASE_DIR, 'recipes_test.db')}"
    )


class ProductionConfig(Config):
    pass