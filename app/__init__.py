import os
from functools import wraps
from flask import Flask, current_app, g, jsonify, request, send_file
from flask_cors import CORS
import jwt

from app.extensions import db, migrate
from config import DevelopmentConfig, ProductionConfig, TestingConfig


def recipe_to_dict(row):
    return {
        "id": row.id,
        "title": row.title,
        "ingredients": row.ingredients,
        "instructions": row.instructions or "",
        "is_public": bool(row.is_public),
        "user_id": row.user_id,
    }


def user_to_dict(row):
    return {
        "id": row.id if hasattr(row, "id") else row["id"],
        "username": row.username if hasattr(row, "username") else row["username"],
        "email": row.email if hasattr(row, "email") else row["email"],
        "role": row.role if hasattr(row, "role") else row["role"],
        "created_at": (
            row.created_at if hasattr(row, "created_at") else row["created_at"]
        ),
    }


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


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    CORS(app)

    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    config_class = config_map.get(config_name, DevelopmentConfig)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Enforce SQLite Foreign Key constraints
    from sqlalchemy import event
    import sqlalchemy.engine

    @event.listens_for(sqlalchemy.engine.Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from app.routes.auth import auth_bp
    from app.routes.recipes import recipes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp, url_prefix="/recipes")

    @app.route("/", methods=["GET"])
    def home():
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        app_dir = os.path.abspath(os.path.dirname(__file__))

        # Check project root first, then app/ directory
        if os.path.exists(os.path.join(root_dir, "index.html")):
            return send_file(os.path.join(root_dir, "index.html"))
        elif os.path.exists(os.path.join(app_dir, "index.html")):
            return send_file(os.path.join(app_dir, "index.html"))

        # Fallback API greeting so it never raises a 500 error
        return (
            jsonify({"message": "Recipe Box API", "recipes": "/recipes"}),
            200,
        )

    return app