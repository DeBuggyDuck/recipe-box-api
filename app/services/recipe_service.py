import sqlite3

from app.models import insert_recipe


def create_recipe(db, user_id: int, data: dict | None) -> tuple[dict | None, str | None]:
    """Execute recipe creation with validation and return the record or an error code.

    Args:
        db: SQLite database connection.
        user_id: The ID of the authenticated user creating the recipe.
        data: Request payload containing title, ingredients, instructions, and is_public flag.

    Returns:
        tuple[dict | None, str | None]:
            - (recipe_dict, None) on successful insertion.
            - (None, "missing_required_fields") if title or ingredients are missing/falsy.
            - (None, "duplicate_title") if a recipe with that title already exists.
    """
    if not data or not data.get("title") or not data.get("ingredients"):
        return None, "missing_required_fields"

    title = data["title"]
    ingredients = data["ingredients"]
    instructions = data.get("instructions", "")
    is_public = 1 if data.get("is_public", True) else 0

    try:
        recipe = insert_recipe(
            db,
            title=title,
            ingredients=ingredients,
            instructions=instructions,
            is_public=is_public,
            user_id=user_id,
        )
        return recipe, None
    except sqlite3.IntegrityError:
        return None, "duplicate_title"