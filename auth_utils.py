"""Password hashing and verification helpers."""

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(plaintext_password: str) -> str:
    """Generate a secure one-way hash from a plaintext password."""
    return generate_password_hash(plaintext_password)


def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """Verify a candidate password against an existing stored hash."""
    return check_password_hash(stored_hash, candidate_password)
