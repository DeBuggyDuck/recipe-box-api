"""Database connection and initialization utilities."""

import sqlite3
from flask import current_app, g


def get_db():
    """Acquire or reuse a SQLite connection for the current application context."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(app=None):
    """Initialize the SQLite database schema and tables.

    Connects to the configured DATABASE path and executes DDL to create the
    'users' and 'recipes' tables if they do not already exist.
    """
    db_path = (
        app.config["DATABASE"] if app else current_app.config["DATABASE"]
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL UNIQUE,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL DEFAULT '',
                is_public INTEGER NOT NULL DEFAULT 1,
                user_id INTEGER REFERENCES users(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()