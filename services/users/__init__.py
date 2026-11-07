from flask import Flask

from services.users.config import UsersConfig
from services.users.extensions import db, migrate


def create_app(config_class=UsersConfig) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db, directory="services/users/migrations")

    from services.users.models import User  # noqa: F401
    from services.users.routes import users_bp

    app.register_blueprint(users_bp)

    return app