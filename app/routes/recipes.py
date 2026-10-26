"""Recipe route handlers and endpoints."""

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import recipe_to_dict, token_required
from app.extensions import cache, db, limiter
from app.models import Recipe
from app.services.recipe_service import (
    add_rating_for_recipe,
    get_recipe_by_id,
    list_recipes_for_user,
)

recipes_bp = Blueprint("recipes", __name__)


# ==========================================
# 1. LIST RECIPES (CACHED)
# ==========================================
@recipes_bp.route("", methods=["GET"])
@cache.cached(timeout=30)
def list_recipes():
    current_user_id = getattr(g, "current_user_id", None)
    current_role = getattr(g, "current_role", "user")

    recipes = list_recipes_for_user(current_user_id, current_role)
    return jsonify(recipes), 200


# ==========================================
# 2. CREATE RECIPE
# ==========================================
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

    cache.clear()
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

    current_user_id = getattr(g, "current_user_id", None)
    current_role = getattr(g, "current_role", "user")

    if recipe.user_id != current_user_id and current_role != "admin":
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You do not own this recipe",
                }
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
    current_user_id = g.current_user_id
    current_role = g.current_role

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "a JSON body is required"}), 400

    allowed_fields = {"title", "ingredients", "instructions", "is_public"}
    if not any(field in data for field in allowed_fields):
        return jsonify({"error": "nothing to update"}), 400

    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    if recipe.user_id != current_user_id and current_role != "admin":
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

    cache.clear()
    return jsonify(recipe_to_dict(recipe)), 200


# ==========================================
# 5. DELETE RECIPE
# ==========================================
@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
@token_required
def delete_recipe(recipe_id: int):
    current_user_id = g.current_user_id
    current_role = g.current_role

    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    if recipe.user_id != current_user_id and current_role != "admin":
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
    cache.clear()

    return "", 204


# ==========================================
# 6. CREATE RATING (RATE-LIMITED)
# ==========================================
@recipes_bp.route("/<int:recipe_id>/ratings", methods=["POST"])
@limiter.limit("10 per minute")
@token_required
def create_rating(recipe_id: int):
    current_user_id = g.current_user_id
    data = request.get_json(silent=True) or {}

    score = data.get("score")
    comment = data.get("comment")

    rating, error = add_rating_for_recipe(
        user_id=current_user_id,
        recipe_id=recipe_id,
        score=score,
        comment=comment,
    )

    if error == "not_found":
        return jsonify({"error": "Not Found", "message": "Recipe not found"}), 404

    if error == "bad_request":
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        "score is required and must be an integer between 1 and 5"
                    ),
                }
            ),
            400,
        )

    if error == "conflict":
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": "You have already rated this recipe",
                }
            ),
            409,
        )

    return jsonify(rating), 201