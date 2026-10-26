"""Recipe service module — domain logic for recipes and ratings."""

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Rating, Recipe


def list_recipes_for_user(
    current_user_id: int | None = None, current_role: str = "user"
) -> list[dict]:
    """Retrieve recipes visible to the caller (public recipes + user's own private recipes)."""
    if current_role == "admin":
        recipes = Recipe.query.all()
    elif current_user_id is not None:
        recipes = Recipe.query.filter(
            (Recipe.is_public == 1) | (Recipe.user_id == current_user_id)
        ).all()
    else:
        recipes = Recipe.query.filter_by(is_public=1).all()

    return [
        {
            "id": r.id,
            "title": r.title,
            "ingredients": r.ingredients,
            "instructions": r.instructions,
            "is_public": bool(r.is_public),
            "user_id": r.user_id,
        }
        for r in recipes
    ]


def get_recipe_by_id(recipe_id: int) -> Recipe | None:
    """Fetch a single recipe by its primary key ID."""
    return Recipe.query.get(recipe_id)


def create_recipe(user_id: int, data: dict) -> tuple[dict | None, str | None]:
    """Validate and persist a new recipe."""
    title = data.get("title")
    ingredients = data.get("ingredients")

    if not title or not ingredients:
        return None, "missing_required_fields"

    recipe = Recipe(
        title=title,
        ingredients=ingredients,
        instructions=data.get("instructions", ""),
        is_public=1 if data.get("is_public", True) else 0,
        user_id=user_id,
    )

    try:
        db.session.add(recipe)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "duplicate_title"

    return {
        "id": recipe.id,
        "title": recipe.title,
        "ingredients": recipe.ingredients,
        "instructions": recipe.instructions,
        "is_public": bool(recipe.is_public),
        "user_id": recipe.user_id,
    }, None


def add_rating_for_recipe(
    user_id: int,
    recipe_id: int,
    score: int,
    comment: str | None = None,
) -> tuple[dict | None, str | None]:
    """Add a rating for a recipe by an authenticated user.

    Returns:
        tuple[dict | None, str | None]:
            - (rating_dict, None) on success
            - (None, "not_found") if the recipe doesn't exist
            - (None, "bad_request") if score is not an integer in [1, 5]
            - (None, "conflict") if the user has already rated this recipe
    """
    # 1. Target recipe existence check
    recipe = Recipe.query.get(recipe_id)
    if recipe is None:
        return None, "not_found"

    # 2. Strict score range and type check
    if not isinstance(score, int) or isinstance(score, bool) or score < 1 or score > 5:
        return None, "bad_request"

    # 3. Check for existing rating by this user
    existing_rating = Rating.query.filter_by(
        user_id=user_id, recipe_id=recipe_id
    ).first()
    if existing_rating is not None:
        return None, "conflict"

    # 4. Insert and commit new rating
    rating = Rating(
        user_id=user_id,
        recipe_id=recipe_id,
        score=score,
        comment=comment,
    )

    try:
        db.session.add(rating)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "conflict"

    return {
        "id": rating.id,
        "score": rating.score,
        "comment": rating.comment,
        "user_id": rating.user_id,
        "recipe_id": rating.recipe_id,
    }, None