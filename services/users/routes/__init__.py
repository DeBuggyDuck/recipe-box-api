from datetime import datetime, timedelta, timezone
from flask import Blueprint, current_app, jsonify, request
import jwt
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from services.users.extensions import db
from services.users.models import User

users_bp = Blueprint("users", __name__)


@users_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(email, str)
        or not email.strip()
        or not isinstance(password, str)
        or not password.strip()
    ):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        "username, email, and password are required non-empty"
                        " strings"
                    ),
                }
            ),
            400,
        )

    clean_username = username.strip()
    clean_email = email.strip()
    hashed_pw = generate_password_hash(password)
    created_at = datetime.now(timezone.utc).isoformat()

    user = User(
        username=clean_username,
        email=clean_email,
        password_hash=hashed_pw,
        created_at=created_at,
        role="user",
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": (
                        "A user with that username or email already exists"
                    ),
                }
            ),
            409,
        )

    return (
        jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at,
        }),
        201,
    )


@users_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(password, str)
        or not password.strip()
    ):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        "username and password are required non-empty strings"
                    ),
                }
            ),
            400,
        )

    clean_username = username.strip()
    user = User.query.filter_by(username=clean_username).first()

    if user is None or not check_password_hash(user.password_hash, password):
        return (
            jsonify(
                {"error": "Unauthorized", "message": "Invalid credentials"}
            ),
            401,
        )

    secret = current_app.config.get("JWT_SECRET") or "dev-secret-key"
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return jsonify({"token": token}), 200