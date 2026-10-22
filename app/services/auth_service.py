from datetime import datetime, timedelta, timezone
from flask import current_app
import jwt
from sqlalchemy.exc import IntegrityError

from app import user_to_dict
from app.extensions import db
from app.models import User
from auth_utils import hash_password, verify_password


def register_user(data: dict) -> tuple[dict | None, str | None]:
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

    user = User(
        username=clean_username,
        email=clean_email,
        password_hash=hashed_pw,
        created_at=created_at,
    )

    try:
        db.session.add(user)
        db.session.commit()
        return user_to_dict(user), None
    except IntegrityError:
        db.session.rollback()
        return None, "user_exists"


def login_user(data: dict) -> tuple[str | None, str | None]:
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
    user = User.query.filter_by(username=clean_username).first()

    if user is None or not verify_password(user.password_hash, password):
        return None, "invalid_credentials"

    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    token = jwt.encode(
        payload, current_app.config["JWT_SECRET"], algorithm="HS256"
    )
    return token, None


def get_current_user(token: str) -> tuple[dict | None, str | None]:
    """Decode and verify JWT, fetch the user via User.query.get, and return (user_dict, error_code)."""
    try:
        claims = jwt.decode(
            token,
            current_app.config["JWT_SECRET"],
            algorithms=["HS256"],
        )
        user_id = claims["user_id"]
    except (jwt.PyJWTError, KeyError):
        return None, "invalid_token"

    user = User.query.get(user_id)
    if user is None:
        return None, "invalid_token"

    return user_to_dict(user), None