"""Recipe route handlers and endpoints for the recipes microservice."""

import os
from flask import Blueprint, current_app, g, jsonify, request
import jwt
from sqlalchemy.exc import IntegrityError

from app import recipe_to_dict, token_required
from app.extensions import db
from app.models import Recipe
from app.services.recipe_service import (
    get_recipe_by_id,
    list_recipes_for_user,
)

recipes_bp = Blueprint("recipes", __name__)


# ==========================================
# 1. LIST RECIPES
# ==========================================
@recipes_bp.route("", methods=["GET"])
def list_recipes():
    current_user_id = None
    current_role = "user"

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            claims = jwt.decode(
                token, current_app.config["JWT_SECRET"], algorithms=["HS256"]
            )
            current_user_id = claims.get("user_id")
            current_role = claims.get("role", "user")
        except (jwt.PyJWTError, KeyError):
            pass

    recipes = list_recipes_for_user(current_user_id, current_role)
    return jsonify(recipes), 200


# ==========================================
# 2. CREATE RECIPE (BOUNDARY C CONTRACT)
# ==========================================
@recipes_bp.route("", methods=["POST"])
def create_recipe():
    # 1. Inspect Boundary C headers
    auth_header = request.headers.get("Authorization")
    internal_token = request.headers.get("X-Internal-Service-Token")

    # 2. Verify end-user JWT (401 on missing or invalid)
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
    except (jwt.PyJWTError, KeyError):
        return (
            jsonify(
                {"error": "Unauthorized", "message": "Missing or invalid token"}
            ),
            401,
        )

    # 3. Verify internal caller identity token (403 on missing or invalid)
    expected_token = os.environ.get(
        "INTERNAL_SERVICE_TOKEN", "dev-internal-secret"
    )
    if not internal_token or internal_token != expected_token:
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "Invalid or missing internal service token",
                }
            ),
            403,
        )

    # 4. Payload validation & creation
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("ingredients"):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "title and ingredients are required",
                }
            ),
            400,
        )

    recipe = Recipe(
        title=data["title"],
        ingredients=data["ingredients"],
        instructions=data.get("instructions", ""),
        is_public=1 if data.get("is_public", True) else 0,
        user_id=current_user_id,
    )

    try:
        db.session.add(recipe)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify({"error": "a recipe with that title already exists"}),
            409,
        )

    return jsonify(recipe_to_dict(recipe)), 201


# ==========================================
# 3. GET SINGLE RECIPE
# ==========================================
@recipes_bp.route("/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id: int):
    recipe = get_recipe_by_id(recipe_id)

    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    if recipe.is_public:
        return jsonify(recipe_to_dict(recipe)), 200

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
        current_user_id = claims.get("user_id")
        current_role = claims.get("role", "user")
    except (jwt.PyJWTError, KeyError):
        return (
            jsonify(
                {"error": "Unauthorized", "message": "Missing or invalid token"}
            ),
            401,
        )

    if recipe.user_id != current_user_id and current_role != "admin":
        return (
            jsonify(
                {"error": "Forbidden", "message": "You do not own this recipe"}
            ),
            403,
        )

    return jsonify(recipe_to_dict(recipe)), 200


# ==========================================
# 4. UPDATE RECIPE
# ==========================================
@recipes_bp.route("/<int:recipe_id>", methods=["PATCH"])
@token_required
def update_recipe(recipe_id: int):
    token_user_id = g.current_user_id
    token_role = g.current_role

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "a JSON body is required"}), 400

    allowed_fields = {"title", "ingredients", "instructions", "is_public"}
    if not any(field in data for field in allowed_fields):
        return jsonify({"error": "nothing to update"}), 400

    recipe = Recipe.query.get(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    if recipe.user_id != token_user_id and token_role != "admin":
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You are not allowed to modify this recipe",
                }
            ),
            403,
        )

    if "title" in data:
        recipe.title = data["title"]
    if "ingredients" in data:
        recipe.ingredients = data["ingredients"]
    if "instructions" in data:
        recipe.instructions = data["instructions"]
    if "is_public" in data:
        recipe.is_public = 1 if data["is_public"] else 0

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify({"error": "a recipe with that title already exists"}),
            409,
        )

    return jsonify(recipe_to_dict(recipe)), 200


# ==========================================
# 5. DELETE RECIPE
# ==========================================
@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
@token_required
def delete_recipe(recipe_id: int):
    token_user_id = g.current_user_id
    token_role = g.current_role

    recipe = Recipe.query.get(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    if recipe.user_id != token_user_id and token_role != "admin":
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You are not allowed to delete this recipe",
                }
            ),
            403,
        )

    db.session.delete(recipe)
    db.session.commit()

    return "", 204