from datetime import datetime, timedelta, timezone
import sqlite3
from flask import current_app
import jwt

from app import user_to_dict
from app.models import create_user, get_user_by_id, get_user_by_username
from auth_utils import hash_password, verify_password


def register_user(db, data: dict) -> tuple[dict | None, str | None]:
    """Execute user registration domain logic and return (user_dict, error_code)."""
    username = data.get("username") if isinstance(data, dict) else None
    email = data.get("email") if isinstance(data, dict) else None
    password = data.get("password") if isinstance(data, dict) else None

    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(email, str)
        or not email.strip()
        or not isinstance(password, str)
        or not password.strip()
    ):
        return None, "validation_error"

    clean_username = username.strip()
    clean_email = email.strip()
    hashed_pw = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        row = create_user(
            db, clean_username, clean_email, hashed_pw, created_at
        )
        return user_to_dict(row), None
    except sqlite3.IntegrityError:
        return None, "user_exists"


def login_user(db, data: dict) -> tuple[str | None, str | None]:
    """Execute user login domain logic and return (token, error_code)."""
    username = data.get("username") if isinstance(data, dict) else None
    password = data.get("password") if isinstance(data, dict) else None

    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(password, str)
        or not password.strip()
    ):
        return None, "validation_error"

    clean_username = username.strip()
    row = get_user_by_username(db, clean_username)

    if row is None or not verify_password(row["password_hash"], password):
        return None, "invalid_credentials"

    payload = {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    token = jwt.encode(
        payload, current_app.config["JWT_SECRET"], algorithm="HS256"
    )
    return token, None


def get_current_user(db, token: str) -> tuple[dict | None, str | None]:
    """Decode and verify JWT, fetch the user via get_user_by_id, and return (user_dict, error_code)."""
    try:
        claims = jwt.decode(
            token,
            current_app.config["JWT_SECRET"],
            algorithms=["HS256"],
        )
        user_id = claims["user_id"]
    except (jwt.PyJWTError, KeyError):
        return None, "invalid_token"

    row = get_user_by_id(db, user_id)
    if row is None:
        return None, "invalid_token"

    return user_to_dict(row), None