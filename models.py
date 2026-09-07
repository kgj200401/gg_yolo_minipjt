from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    price = Column(Integer, nullable=False)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.ingredient_order",
    )
    steps = relationship(
        "RecipeStep",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeStep.step_number",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    ingredient_order = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False, default=1)
    unit = Column(String, nullable=False, default="개")

    recipe = relationship("Recipe", back_populates="ingredients")
    product = relationship("Product")


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)

    recipe = relationship("Recipe", back_populates="steps")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        unique=True,
        nullable=False,
    )
    quantity = Column(Integer, nullable=False, default=1)

    product = relationship("Product")
