class Config:
    DEBUG = False
    TESTING = False
    DATABASE = "recipes.db"
    JWT_SECRET = None


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE = "recipes_test.db"


class ProductionConfig(Config):
    pass