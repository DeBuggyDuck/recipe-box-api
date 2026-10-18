import sqlite3


def insert_recipe(
    db: sqlite3.Connection,
    title: str,
    ingredients: str,
    instructions: str,
    is_public: int,
    user_id: int,
) -> dict:
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


def create_user(
    db: sqlite3.Connection,
    username: str,
    email: str,
    password_hash: str,
    created_at: str,
) -> sqlite3.Row:
    """Insert a new user record and return the created database row.

    Raises:
        sqlite3.IntegrityError: If the username or email already exists.
    """
    cur = db.execute(
        "INSERT INTO users (username, email, password_hash, created_at) "
        "VALUES (?, ?, ?, ?)",
        (username, email, password_hash, created_at),
    )
    db.commit()

    return db.execute(
        "SELECT id, username, email, role, created_at FROM users WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()


def get_user_by_username(
    db: sqlite3.Connection, username: str
) -> sqlite3.Row | None:
    """Fetch a single user row by username, or return None if not found."""
    return db.execute(
        "SELECT id, username, email, password_hash, role, created_at "
        "FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def get_user_by_id(db: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    """Fetch a single user row by its primary key ID, or return None."""
    return db.execute(
        "SELECT id, username, email, role, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()