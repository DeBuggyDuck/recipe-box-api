"""Recipe Box API — BE104 course skeleton.

A working Flask + SQLite CRUD API for recipes and users.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
import os
import sqlite3

from auth_utils import hash_password, verify_password
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
import jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")

DATABASE = "recipes.db"

app = Flask(__name__)


# ==========================================
# DATABASE LIFECYCLE
# ==========================================


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ==========================================
# SERIALIZATION HELPERS
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


# ==========================================
# AUTHENTICATION MIDDLEWARE / DECORATOR
# ==========================================


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
            claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
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
# DEBUG ROUTES
# ==========================================


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


# ==========================================
# AUTHENTICATION / USER ROUTES
# ==========================================


@app.route("/register", methods=["POST"])
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


@app.route("/login", methods=["POST"])
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

    # Issue signed JWT with identity and role claims
    payload = {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return jsonify({"token": token}), 200


# ==========================================
# RECIPE ROUTES
# ==========================================


@app.route("/", methods=["GET"])
def hello():
    return jsonify({"message": "Recipe Box API", "recipes": "/recipes"})


@app.route("/recipes", methods=["GET"])
def list_recipes():
    db = get_db()
    current_user_id = None

    # Optional bearer token check
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user_id = claims.get("user_id")
        except (jwt.PyJWTError, KeyError):
            pass

    if current_user_id is not None:
        rows = db.execute(
            "SELECT * FROM recipes WHERE is_public = 1 OR user_id = ? ORDER BY"
            " id",
            (current_user_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM recipes WHERE is_public = 1 ORDER BY id"
        ).fetchall()

    return jsonify([recipe_to_dict(r) for r in rows]), 200


@app.route("/recipes/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "recipe not found"}), 404

    # Public recipes require no auth
    if row["is_public"]:
        return jsonify(recipe_to_dict(row)), 200

    # Private recipes require verified token matching owner
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
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        current_user_id = claims["user_id"]
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

    if row["user_id"] != current_user_id:
        return (
            jsonify(
                {"error": "Forbidden", "message": "You do not own this recipe"}
            ),
            403,
        )

    return jsonify(recipe_to_dict(row)), 200


@app.route("/recipes", methods=["POST"])
@token_required
def create_recipe():
    current_user_id = g.current_user_id

    data = request.get_json(silent=True)
    if not data or not data.get("title") or not data.get("ingredients"):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "title and ingredients are required",
                }
            ),
            400,
        )

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO recipes (title, ingredients, instructions, is_public,"
            " user_id) VALUES (?, ?, ?, ?, ?)",
            (
                data["title"],
                data["ingredients"],
                data.get("instructions", ""),
                1 if data.get("is_public", True) else 0,
                current_user_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return (
            jsonify({"error": "a recipe with that title already exists"}),
            409,
        )

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(recipe_to_dict(row)), 201


@app.route("/recipes/<int:recipe_id>", methods=["PATCH"])
@token_required
def update_recipe(recipe_id):
    current_user_id = g.current_user_id
    current_role = g.current_role

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "a JSON body is required"}), 400

    fields, values = [], []
    for column in ("title", "ingredients", "instructions"):
        if column in data:
            fields.append(f"{column} = ?")
            values.append(data[column])
    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)
    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    db = get_db()
    recipe = db.execute(
        "SELECT user_id FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()

    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    # Ownership check with admin override
    if recipe["user_id"] != current_user_id and current_role != "admin":
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You are not allowed to modify this recipe",
                }
            ),
            403,
        )

    values.append(recipe_id)
    try:
        db.execute(
            f"UPDATE recipes SET {', '.join(fields)} WHERE id = ?", values
        )
        db.commit()
    except sqlite3.IntegrityError:
        return (
            jsonify({"error": "a recipe with that title already exists"}),
            409,
        )

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    return jsonify(recipe_to_dict(row)), 200


@app.route("/recipes/<int:recipe_id>", methods=["DELETE"])
@token_required
def delete_recipe(recipe_id):
    current_user_id = g.current_user_id
    current_role = g.current_role

    db = get_db()
    recipe = db.execute(
        "SELECT user_id FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()

    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    # Ownership check with admin override
    if recipe["user_id"] != current_user_id and current_role != "admin":
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You are not allowed to delete this recipe",
                }
            ),
            403,
        )

    db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    db.commit()

    return "", 204


if __name__ == "__main__":
    app.run(port=5001, debug=True)