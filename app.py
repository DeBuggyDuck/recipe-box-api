"""Recipe Box API — BE104 course skeleton.

A working Flask + SQLite CRUD API for recipes and users.
"""

from datetime import datetime, timezone
import sqlite3

from flask import Flask, g, jsonify, request, abort

from auth_utils import hash_password, verify_password

DATABASE = "recipes.db"

app = Flask(__name__)


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


def recipe_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


def user_to_dict(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


@app.route("/debug/hash-test")
def hash_test():
    pw = "TempPass123!"  # hard-coded test password, not real user data
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
        return jsonify({
            "error": "Bad Request",
            "message": "Request body must be valid JSON"
        }), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # 1. Enforce non-empty string types
    if (
        not isinstance(username, str) or not username.strip() or
        not isinstance(email, str) or not email.strip() or
        not isinstance(password, str) or not password.strip()
    ):
        return jsonify({
            "error": "Bad Request",
            "message": "username, email, and password are required non-empty strings"
        }), 400

    clean_username = username.strip()
    clean_email = email.strip()

    db = get_db()
    hashed_pw = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()

    # 2. Insert with collision handling (409 Conflict)
    try:
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (clean_username, clean_email, hashed_pw, created_at),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({
            "error": "Conflict",
            "message": "A user with that username or email already exists"
        }), 409

    # 3. Retrieve and return the created record via safe dict serializer
    row = db.execute(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()

    return jsonify(user_to_dict(row)), 201


# ==========================================
# AUTHENTICATION / LOGIN ROUTE
# ==========================================


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

    # Enforce non-empty string types
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
        "SELECT id, username, email, password_hash, created_at FROM users"
        " WHERE username = ?"
    )
    row = db.execute(query, (username.strip(),)).fetchone()

    # User not found or hash verification failed -> 401 Unauthorized
    if row is None or not verify_password(row["password_hash"], password):
        return (
            jsonify(
                {"error": "Unauthorized", "message": "Invalid credentials"}
            ),
            401,
        )

    return jsonify(user_to_dict(row)), 200


# ==========================================
# RECIPE ROUTES
# ==========================================


@app.route("/", methods=["GET"])
def hello():
    return jsonify({"message": "Recipe Box API", "recipes": "/recipes"})


@app.route("/recipes", methods=["GET"])
def list_recipes():
    rows = get_db().execute("SELECT * FROM recipes ORDER BY id").fetchall()
    return jsonify([recipe_to_dict(r) for r in rows])


@app.route("/recipes/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
    row = get_db().execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "recipe not found"}), 404
    return jsonify(recipe_to_dict(row))


@app.route("/recipes", methods=["POST"])
def create_recipe():
    data = request.get_json(silent=True)
    if not data or not data.get("title") or not data.get("ingredients"):
        return jsonify({"error": "title and ingredients are required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO recipes (title, ingredients, instructions, is_public) "
            "VALUES (?, ?, ?, ?)",
            (
                data["title"],
                data["ingredients"],
                data.get("instructions", ""),
                1 if data.get("is_public", True) else 0,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(recipe_to_dict(row)), 201


@app.route("/recipes/<int:recipe_id>", methods=["PATCH"])
def update_recipe(recipe_id):
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
    values.append(recipe_id)
    db = get_db()
    try:
        cur = db.execute(
            f"UPDATE recipes SET {', '.join(fields)} WHERE id = ?", values
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "recipe not found"}), 404
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    return jsonify(recipe_to_dict(row))


@app.route("/recipes/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    db = get_db()
    cur = db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "recipe not found"}), 404
    return "", 204


if __name__ == "__main__":
    app.run(port=5001, debug=True)