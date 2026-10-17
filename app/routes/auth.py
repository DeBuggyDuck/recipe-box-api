from datetime import datetime, timedelta, timezone
import sqlite3
from flask import Blueprint, current_app, jsonify, request
import jwt

from app import get_db, user_to_dict
from auth_utils import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not data:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Request body must be valid JSON",
                }
            ),
            400,
        )

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

    db = get_db()
    hashed_pw = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (clean_username, clean_email, hashed_pw, created_at),
        )
        db.commit()
    except sqlite3.IntegrityError:
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

    row = db.execute(
        "SELECT id, username, email, role, created_at FROM users WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()

    return jsonify(user_to_dict(row)), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Request body must be valid JSON",
                }
            ),
            400,
        )

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

    db = get_db()
    query = (
        "SELECT id, username, email, password_hash, role, created_at "
        "FROM users WHERE username = ?"
    )
    row = db.execute(query, (username.strip(),)).fetchone()

    if row is None or not verify_password(row["password_hash"], password):
        return (
            jsonify(
                {"error": "Unauthorized", "message": "Invalid credentials"}
            ),
            401,
        )

    payload = {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    token = jwt.encode(
        payload, current_app.config["JWT_SECRET"], algorithm="HS256"
    )
    return jsonify({"token": token}), 200