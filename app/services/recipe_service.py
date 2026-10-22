from sqlalchemy import or_

from app import recipe_to_dict
from app.models import Recipe


def list_recipes_for_user(
    current_user_id: int | None,
    current_role: str = "user",
) -> list[dict]:
    query = Recipe.query

    if current_role == "admin":
        recipes = query.order_by(Recipe.id.asc()).all()
    elif current_user_id is not None:
        recipes = (
            query.filter(
                or_(Recipe.is_public == 1, Recipe.user_id == current_user_id)
            )
            .order_by(Recipe.id.asc())
            .all()
        )
    else:
        recipes = (
            query.filter(Recipe.is_public == 1)
            .order_by(Recipe.id.asc())
            .all()
        )

    return [recipe_to_dict(r) for r in recipes]


def get_recipe_by_id(recipe_id: int) -> Recipe | None:
    return Recipe.query.get(recipe_id)