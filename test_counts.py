import sqlite3


def counts(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM recipes")
    recipes = cur.fetchone()[0]
    conn.close()
    return {"users": users, "recipes": recipes}

print("DEV (recipes.db):", counts("recipes.db"))
print("TEST (recipes_test.db):", counts("recipes_test.db"))