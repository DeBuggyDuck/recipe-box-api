import sqlite3


def insert_recipe(db: sqlite3.Connection, title: str, ingredients: str, instructions: str, is_public: int, user_id: int) -> dict:
    """Insert a recipe into the database and return the newly created row as a dict.

    Raises:
        sqlite3.IntegrityError: If a uniqueness or foreign key constraint is violated.
    """
    cur = db.execute(
        "INSERT INTO recipes (title, ingredients, instructions, is_public, user_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, ingredients, instructions, is_public, user_id),
    )
    db.commit()

    row = db.execute(
        "SELECT id, title, ingredients, instructions, is_public, user_id "
        "FROM recipes WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()

    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
        "user_id": row["user_id"],
    }