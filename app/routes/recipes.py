import sqlite3
from app.services.recipe_service import create_recipe as create_recipe_service
from flask import Blueprint, current_app, g, jsonify, request
import jwt

from app import get_db, recipe_to_dict, token_required

recipes_bp = Blueprint("recipes", __name__)


@recipes_bp.route("", methods=["POST"])
@token_required
def create_recipe():
    current_user_id = g.current_user_id
    data = request.get_json(silent=True)

    db = get_db()
    recipe, error = create_recipe_service(db, current_user_id, data)

    if error == "missing_required_fields":
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "title and ingredients are required",
                }
            ),
            400,
        )

    if error == "duplicate_title":
        return (
            jsonify({"error": "a recipe with that title already exists"}),
            409,
        )

    return jsonify(recipe), 201

@recipes_bp.route("/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "recipe not found"}), 404

    if row["is_public"]:
        return jsonify(recipe_to_dict(row)), 200

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


@recipes_bp.route("", methods=["POST"])
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


@recipes_bp.route("/<int:recipe_id>", methods=["PATCH"])
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


@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
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