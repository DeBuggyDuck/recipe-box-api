from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    created_at = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False, server_default="user")

    recipes = db.relationship("Recipe", back_populates="user")
    ratings = db.relationship(
        "Rating", back_populates="user", cascade="all, delete-orphan"
    )


class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False, server_default="")
    is_public = db.Column(db.Integer, nullable=False, server_default="1")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", back_populates="recipes")
    ratings = db.relationship(
        "Rating", back_populates="recipe", cascade="all, delete-orphan"
    )


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True, default=None)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "recipe_id", name="uq_rating_user_recipe"
        ),
    )

    user = db.relationship("User", back_populates="ratings")
    recipe = db.relationship("Recipe", back_populates="ratings")