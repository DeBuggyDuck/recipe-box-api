"""Recipe Box API — BE104 course skeleton.

A working Flask + SQLite CRUD API for recipes and users.
"""

from functools import wraps
import os
import sqlite3

from auth_utils import hash_password, verify_password
from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from dotenv import load_dotenv
from flask import Flask, current_app, g, jsonify, request, send_file
from flask_cors import CORS
import jwt

from app.db import init_db

load_dotenv()

# ==========================================
# MODULE-LEVEL HELPERS & MIDDLEWARE
# ==========================================


def recipe_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
        "user_id": row["user_id"],
    }


def user_to_dict(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Missing or invalid token",
                    }
                ),
                401,
            )

        token = auth_header.split(" ", 1)[1]
        try:
            jwt_secret = os.getenv("JWT_SECRET")
            claims = jwt.decode(token, jwt_secret, algorithms=["HS256"])
            g.current_user_id = claims["user_id"]
            g.current_role = claims.get("role")
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
                    {
                        "error": "Unauthorized",
                        "message": "Missing or invalid token",
                    }
                ),
                401,
            )

        return f(*args, **kwargs)

    return wrapper


# ==========================================
# APPLICATION FACTORY
# ==========================================


def create_app(config_name: str | None = None) -> Flask:
    from app.routes.auth import auth_bp
    from app.routes.recipes import recipes_bp

    app = Flask(__name__)
    CORS(app)

    # 1. Environment & Config Loading
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    config_class = config_map.get(config_name, DevelopmentConfig)
    app.config.from_object(config_class)

    # 2. Database Schema Initialization
    init_db(app)

    # 3. Blueprint Registration
    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp, url_prefix="/recipes")

    # 4. Context Teardown
    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # 5. Non-API / Static / Debug Routes
    @app.route("/debug/hash-test")
    def hash_test():
        pw = "TempPass123!"
        h = hash_password(pw)
        ok = verify_password(h, pw)
        bad = verify_password(h, "WrongPass!")

        return {
            "hash_starts_with": h[:30],
            "hash_looks_long": len(h) >= 60,
            "correct_check": ok,
            "wrong_check": bad,
        }

    @app.route("/", methods=["GET"])
    def home():
        return send_file("index.html")

    return app