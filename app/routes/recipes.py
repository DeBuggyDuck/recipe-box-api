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

    return jsonify(recipe_to_dict(recipe)), 201


@recipes_bp.route("/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
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

    if recipe.user_id != current_user_id:
        return (
            jsonify(
                {"error": "Forbidden", "message": "You do not own this recipe"}
            ),
            403,
        )

    return jsonify(recipe_to_dict(recipe)), 200


@recipes_bp.route("/<int:recipe_id>", methods=["PATCH"])
@token_required
def update_recipe(recipe_id):
    current_user_id = g.current_user_id
    current_role = g.current_role

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "a JSON body is required"}), 400

    allowed_fields = {"title", "ingredients", "instructions", "is_public"}
    if not any(field in data for field in allowed_fields):
        return jsonify({"error": "nothing to update"}), 400

    recipe = Recipe.query.get(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    if recipe.user.id != current_user_id and current_role != "admin":
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


@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
@token_required
def delete_recipe(recipe_id):
    current_user_id = g.current_user_id
    current_role = g.current_role

    recipe = Recipe.query.get(recipe_id)
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

    return "", 204