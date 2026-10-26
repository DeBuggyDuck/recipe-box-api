"""Recipe Box API — application package and factory."""

import os
from functools import wraps

from flask import Flask, current_app, g, jsonify, request, send_file
from flask_cors import CORS
import jwt

from app.extensions import db, migrate, cache, limiter
from config import DevelopmentConfig, ProductionConfig, TestingConfig


# ==========================================
# SERIALIZERS
# ==========================================

def recipe_to_dict(row):
    """Serialize a recipe whether it is a SQLAlchemy ORM model or an SQLite Row."""
    is_public = getattr(row, "is_public", None)
    if is_public is None and hasattr(row, "__getitem__"):
        is_public = row["is_public"]

    def _get(field):
        val = getattr(row, field, None)
        if val is None and hasattr(row, "__getitem__"):
            return row[field]
        return val

    return {
        "id": _get("id"),
        "title": _get("title"),
        "ingredients": _get("ingredients"),
        "instructions": _get("instructions") or "",
        "is_public": bool(is_public),
        "user_id": _get("user_id"),
    }


def user_to_dict(row):
    """Serialize a user record to a safe public dictionary."""
    def _get(field):
        val = getattr(row, field, None)
        if val is None and hasattr(row, "__getitem__"):
            return row[field]
        return val

    return {
        "id": _get("id"),
        "username": _get("username"),
        "email": _get("email"),
        "role": _get("role"),
        "created_at": _get("created_at"),
    }


# ==========================================
# AUTH MIDDLEWARE / DECORATORS
# ==========================================

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {"error": "Unauthorized", "message": "Missing or invalid token"}
                ),
                401,
            )

        token = auth_header.split(" ", 1)[1]
        try:
            claims = jwt.decode(
                token, current_app.config["JWT_SECRET"], algorithms=["HS256"]
            )
            g.current_user_id = claims["user_id"]
            g.current_role = claims.get("role", "user")
        except jwt.ExpiredSignatureError:
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Token has expired. Please log in again.",
                    }
                ),
                401,
            )
        except (jwt.PyJWTError, KeyError):
            return (
                jsonify(
                    {"error": "Unauthorized", "message": "Missing or invalid token"}
                ),
                401,
            )

        return f(*args, **kwargs)

    return decorated


# ==========================================
# APPLICATION FACTORY
# ==========================================

def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    CORS(app)

    # 1. Config loading
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    config_class = config_map.get(config_name, DevelopmentConfig)
    app.config.from_object(config_class)

    # 2. Extensions initialization
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

    # Enforce SQLite Foreign Key constraints
    from sqlalchemy import event
    import sqlalchemy.engine

    @event.listens_for(sqlalchemy.engine.Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # 3. Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.recipes import recipes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp, url_prefix="/recipes")

    # 4. Static / fallback root route
    @app.route("/", methods=["GET"])
    def home():
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        app_dir = os.path.abspath(os.path.dirname(__file__))

        if os.path.exists(os.path.join(root_dir, "index.html")):
            return send_file(os.path.join(root_dir, "index.html"))
        elif os.path.exists(os.path.join(app_dir, "index.html")):
            return send_file(os.path.join(app_dir, "index.html"))

        return (
            jsonify({"message": "Recipe Box API", "recipes": "/recipes"}),
            200,
        )

    return app