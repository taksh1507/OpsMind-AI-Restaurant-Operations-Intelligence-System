"""Menu Models - Categories, Menu Items, Ingredients, and Recipes

Represents the restaurant's menu structure and ingredient composition.
Each category and menu item belongs to exactly one tenant (restaurant).
Recipes define the ingredients and quantities needed for each dish.
"""

from typing import Optional
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Boolean, Numeric, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Category(BaseModel):
    """
    Menu category (e.g., "Starters", "Main Course", "Desserts").
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        name: Category name (e.g., "Starters")
        description: Optional description of the category
        is_active: Whether this category is available in the menu
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    menu_items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class MenuItem(BaseModel):
    """
    Menu item (dish) within a category.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        category_id: Foreign key to parent category
        name: Dish name
        description: Description of the dish
        price: Selling price
        cost_price: Cost to prepare (for profit calculation)
        is_available: Whether this item can be ordered
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "menu_items"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Price stored as Numeric for financial accuracy (not float)
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False
    )
    
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False
    )
    
    # Import tracking for currency-linked pricing
    is_imported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Cost in USD for imported items (used to calculate INR cost with live rates)
    import_cost_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True
    )
    
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    category = relationship("Category", back_populates="menu_items")
    recipes = relationship("Recipe", back_populates="menu_item", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<MenuItem(id={self.id}, name={self.name}, category_id={self.category_id}, tenant_id={self.tenant_id})>"
    
    @property
    def profit_margin(self) -> Decimal:
        """Calculate profit margin as percentage (price - cost_price) / price * 100"""
        if self.price == 0:
            return Decimal(0)
        return ((self.price - self.cost_price) / self.price) * 100


class Ingredient(BaseModel):
    """
    Individual ingredient (raw material) used in recipes.
    
    Tracks unit cost and inventory unit (kg, liters, pieces, etc.)
    to enable precise COGS calculations.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        name: Ingredient name (e.g., "Cheddar Cheese", "Ground Beef")
        unit: Unit of measurement (kg, l, pc, g, ml)
        unit_cost: Cost per unit (in currency)
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "ingredients"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pc"  # pc = pieces, kg = kilogram, l = liter, g = gram, ml = milliliter
    )
    
    # Unit cost stored as Numeric for financial accuracy
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=False
    )
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    recipes = relationship("Recipe", back_populates="ingredient")
    
    def __repr__(self) -> str:
        return f"<Ingredient(id={self.id}, name={self.name}, unit={self.unit}, unit_cost={self.unit_cost}, tenant_id={self.tenant_id})>"


class Recipe(BaseModel):
    """
    Recipe association table linking MenuItem to Ingredients.
    
    Defines what ingredients are used in each dish and in what quantities.
    This enables precise cost calculation per dish.
    
    Attributes:
        id: Unique auto-incremented identifier
        menu_item_id: Foreign key to MenuItem
        ingredient_id: Foreign key to Ingredient
        quantity_used: Amount of ingredient used (in ingredient's unit)
        created_at: Timestamp when created
        updated_at: Timestamp of last update
        
    Example:
        For "Cheese Burger":
        - Recipe(menu_item_id=5, ingredient_id=10, quantity_used=0.2) # 200g Ground Beef
        - Recipe(menu_item_id=5, ingredient_id=15, quantity_used=0.03) # 30g Cheese
    """
    
    __tablename__ = "recipes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Quantity used in ingredient's unit (e.g., 0.2 kg, 0.05 l, 2 pieces)
    quantity_used: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    
    # Relationships
    menu_item = relationship("MenuItem", back_populates="recipes")
    ingredient = relationship("Ingredient", back_populates="recipes")
    
    def __repr__(self) -> str:
        return f"<Recipe(menu_item_id={self.menu_item_id}, ingredient_id={self.ingredient_id}, qty={self.quantity_used})>"
    
    @property
    def ingredient_cost(self) -> Decimal:
        """Total cost of this ingredient in the recipe."""
        return self.ingredient.unit_cost * Decimal(str(self.quantity_used))
