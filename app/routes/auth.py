from flask import Blueprint, jsonify, request

from app.services.auth_service import get_current_user, login_user, register_user

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

    user, error = register_user(data)

    if error == "validation_error":
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

    if error == "user_exists":
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

    return jsonify(user), 201


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

    token, error = login_user(data)

    if error == "validation_error":
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

    if error == "invalid_credentials":
        return (
            jsonify(
                {"error": "Unauthorized", "message": "Invalid credentials"}
            ),
            401,
        )

    return jsonify({"token": token}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
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
    user, error = get_current_user(token)

    if error == "invalid_token":
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "message": "Missing or invalid token",
                }
            ),
            401,
        )

    return jsonify(user), 200