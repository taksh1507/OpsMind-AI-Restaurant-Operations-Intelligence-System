"""
Database Seeding Script for OpsMind AI - Live Demo Setup

This script populates the database with realistic demo data for:
- Test restaurant (tenant)
- Menu items with costs
- 50-100 sales transactions over 14 days
- Customer reviews with sentiment
- Staff schedules

Run with: python scripts/seed_data.py

This enables instant "wow" demonstrations during interviews showing:
✨ AI Strategy Agent analyzing the restaurant
📈 Revenue forecasting with confidence scores  
💰 Profit margin analysis and optimization
👥 Labor efficiency heatmaps
⭐ Customer sentiment analysis
🌍 Weather-aware recommendations
✅ AI recommendation impact tracking
"""

import asyncio
import random
import sys
import io
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core import settings
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.menu import Category, MenuItem, Ingredient, Recipe
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.models.review import Review
from app.models.staff import Staff, Shift, StaffRole

# Use bcrypt directly to avoid passlib compatibility issue
import bcrypt

def hash_password_simple(password: str) -> str:
    """Simple password hashing using bcrypt directly."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


# Demo data templates
RESTAURANT_NAME = "Aurora's Kitchen - Demo Restaurant"
DEMO_EMAIL = "demo@aurora-kitchen.com"
DEMO_PASSWORD = "demo123"

CATEGORIES = [
    {"name": "Burgers", "description": "Premium handcrafted burgers"},
    {"name": "Pizza", "description": "Wood-fired Neapolitan pizza"},
    {"name": "Pasta", "description": "Fresh Italian pasta dishes"},
    {"name": "Salads", "description": "Fresh seasonal salads"},
    {"name": "Appetizers", "description": "Starters and shareable plates"},
    {"name": "Beverages", "description": "Drinks and refreshments"},
    {"name": "Desserts", "description": "Sweet endings"},
]

# Menu items: name, category, price, cost_price, description
MENU_ITEMS = [
    ("Signature Burger", "Burgers", 16.99, 4.50, "Juicy beef with heritage bacon and special sauce"),
    ("Truffle Burger", "Burgers", 22.50, 7.00, "Premium beef with truffle aioli and arugula"),
    ("Classic Cheeseburger", "Burgers", 14.99, 3.80, "Simple perfection with aged cheddar"),
    
    ("Margherita Pizza", "Pizza", 14.99, 3.50, "Tomato, mozzarella, fresh basil"),
    ("Pepperoni Paradise", "Pizza", 16.99, 4.50, "House-made pepperoni and double cheese"),
    ("Vegetarian Delight", "Pizza", 15.99, 4.00, "Seasonal vegetables and fresh herbs"),
    ("Goat Cheese & Fig", "Pizza", 18.99, 5.50, "Creamy goat cheese with caramelized onions"),
    
    ("Cacio e Pepe", "Pasta", 13.99, 2.50, "Creamy pecorino romano and black pepper"),
    ("Carbonara", "Pasta", 14.99, 3.00, "Eggs, bacon, and Parmigiano-Reggiano"),
    ("Seafood Linguine", "Pasta", 19.99, 8.00, "Fresh clams, mussels, and shrimp"),
    
    ("Garden Fresh Salad", "Salads", 10.99, 2.00, "Mixed greens, seasonal vegetables"),
    ("Caesar Salad", "Salads", 11.99, 2.50, "Romaine, house-made croutons, Parmigiano"),
    ("Grilled Shrimp Salad", "Salads", 16.99, 6.00, "Mixed greens with grilled shrimp"),
    
    ("Bruschetta", "Appetizers", 8.99, 1.50, "Tomato, garlic, basil on crispy bread"),
    ("Calamari Fritti", "Appetizers", 12.99, 3.50, "Tender squid with marinara sauce"),
    ("Antipasto Platter", "Appetizers", 18.99, 6.00, "Cured meats, cheeses, pickled vegetables"),
    
    ("House Wine (Glass)", "Beverages", 7.99, 1.50, "Red or White selection"),
    ("Craft Beer", "Beverages", 6.99, 1.80, "Local brewery selection"),
    ("Espresso", "Beverages", 3.99, 0.50, "Fresh Italian espresso"),
    ("Soft Drink", "Beverages", 2.99, 0.30, "Coke, Sprite, or local options"),
    
    ("Tiramisu", "Desserts", 8.99, 1.50, "Classic Italian mascarpone dessert"),
    ("Panna Cotta", "Desserts", 7.99, 1.20, "Silky vanilla cream with berry compote"),
    ("Gelato Trio", "Desserts", 6.99, 1.00, "Three scoops of seasonal gelato"),
]

POSITIVE_REVIEWS = [
    "Absolutely delicious! The food was amazing and the service was top-notch.",
    "Best pizza I've had in years! Highly recommend.",
    "The pasta was perfectly cooked and the sauce was incredible.",
    "Outstanding experience from start to finish. Will definitely return!",
    "Every dish was a masterpiece. The chef clearly knows what they're doing.",
    "Fresh ingredients, beautiful presentation, and friendly staff. 5 stars!",
    "This is now my favorite restaurant in the city. Can't wait to come back.",
    "Exceptional quality and attention to detail. Worth every penny!",
]

NEUTRAL_REVIEWS = [
    "Good food and nice atmosphere. Standard dining experience.",
    "Solid restaurant with reliable quality. Worth a visit.",
    "The food was okay, nothing extraordinary but satisfactory.",
    "Decent options on the menu and reasonable prices.",
    "Had a nice time here. Would visit again if in the area.",
]

NEGATIVE_REVIEWS = [
    "Service was slow and the food came out cold.",
    "Expected better quality for the price. Disappointed.",
    "The noise level was unbearable and our order was wrong.",
    "Food was bland and the waiter seemed uninterested.",
    "Long wait times and mediocre food quality. Not impressed.",
]

STAFF_NAMES = [
    ("Alice Johnson", StaffRole.CHEF),
    ("Bob Rodriguez", StaffRole.SOUS_CHEF),
    ("Carmen Liu", StaffRole.WAITER),
    ("David Smith", StaffRole.WAITER),
    ("Emma Wilson", StaffRole.BARTENDER),
    ("Frank Miller", StaffRole.HOST),
    ("Grace Lee", StaffRole.MANAGER),
    ("Henry Brown", StaffRole.PREP_COOK),
]


async def create_tables(engine):
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created/verified")


async def clear_demo_data(session: AsyncSession, tenant_id: int):
    """Clear existing demo data for clean reseeding."""
    try:
        # Delete sales items first (foreign key constraint)
        stmt_sale_ids = select(Sale.id).where(Sale.tenant_id == tenant_id)
        await session.execute(delete(SaleItem).where(
            SaleItem.sale_id.in_(stmt_sale_ids)
        ))
        
        # Delete other data
        await session.execute(delete(Sale).where(Sale.tenant_id == tenant_id))
        await session.execute(delete(Review).where(Review.tenant_id == tenant_id))
        await session.execute(delete(Shift).where(Shift.tenant_id == tenant_id))
        await session.execute(delete(Staff).where(Staff.tenant_id == tenant_id))
        await session.execute(delete(Recipe).where(Recipe.tenant_id == tenant_id))
        await session.execute(delete(MenuItem).where(MenuItem.tenant_id == tenant_id))
        await session.execute(delete(Category).where(Category.tenant_id == tenant_id))
        await session.commit()
        print("🧹 Cleared existing demo data")
    except Exception as e:
        print(f"⚠️  Could not clear old data: {e}")


async def seed_database():
    """Main seeding function."""
    
    # Use SQLite for local demo (PostgreSQL requires server running)
    # Override the settings database URL for seed script compatibility
    database_url = "sqlite+aiosqlite:///./opsmind_demo.db"
    
    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True
    )
    
    # Create tables
    await create_tables(engine)
    
    # Create async session factory
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )
    
    async with AsyncSessionLocal() as session:
        try:
            # ============ STEP 1: Create Tenant (Restaurant) ============
            print("\n📍 Step 1: Creating demo restaurant (tenant)...")
            
            tenant = Tenant(
                tenant_id="auroras-kitchen-demo",
                name=RESTAURANT_NAME,
                subscription_status="active"
            )
            session.add(tenant)
            await session.flush()  # Get tenant ID
            
            print(f"✅ Restaurant created: {RESTAURANT_NAME} (ID: {tenant.id})")
            
            # ============ STEP 2: Create User ============
            print("\n👤 Step 2: Creating demo user...")
            
            user = User(
                tenant_id=tenant.id,
                email=DEMO_EMAIL,
                hashed_password=hash_password_simple(DEMO_PASSWORD),
                is_active=True,
                is_admin=True
            )
            session.add(user)
            await session.flush()
            
            print(f"✅ User created: {DEMO_EMAIL}")
            print(f"   Password: {DEMO_PASSWORD}")
            
            # ============ STEP 3: Create Categories ============
            print("\n🏷️  Step 3: Creating menu categories...")
            
            categories = {}
            for cat_data in CATEGORIES:
                category = Category(
                    tenant_id=tenant.id,
                    name=cat_data["name"],
                    description=cat_data["description"]
                )
                session.add(category)
                await session.flush()
                categories[cat_data["name"]] = category
            
            print(f"✅ Created {len(categories)} categories")
            
            # ============ STEP 4: Create Menu Items ============
            print("\n🍽️  Step 4: Creating menu items...")
            
            menu_items = []
            for name, category_name, price, cost_price, description in MENU_ITEMS:
                item = MenuItem(
                    tenant_id=tenant.id,
                    category_id=categories[category_name].id,
                    name=name,
                    description=description,
                    price=Decimal(str(price)),
                    cost_price=Decimal(str(cost_price))
                )
                session.add(item)
                await session.flush()
                menu_items.append(item)
            
            print(f"✅ Created {len(menu_items)} menu items")
            
            # ============ STEP 5: Generate Sales Data ============
            print("\n💳 Step 5: Generating 14 days of realistic sales data...")
            
            sales_count = 0
            from_date = datetime.now() - timedelta(days=14)
            
            # Define realistic hourly patterns (lunch/dinner rushes)
            lunch_hours = [12, 13]  # 12-2 PM
            dinner_hours = [19, 20, 21]  # 7-10 PM
            
            for day_offset in range(14):
                sale_date = from_date + timedelta(days=day_offset)
                
                # Skip closed Mondays (optional)
                if sale_date.weekday() == 0:  # Monday
                    continue
                
                # Generate 5-12 transactions per day based on day of week
                num_transactions = random.randint(7, 12) if sale_date.weekday() < 5 else random.randint(10, 15)
                
                for _ in range(num_transactions):
                    # Random time (lunch or dinner)
                    hour = random.choice(lunch_hours + dinner_hours)
                    minute = random.randint(0, 59)
                    
                    sale_datetime = sale_date.replace(hour=hour, minute=minute)
                    
                    # Create sale
                    sale = Sale(
                        tenant_id=tenant.id,
                        timestamp=sale_datetime,
                        payment_method=random.choice([PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.DIGITAL_WALLET]),
                        total_amount=Decimal("0"),  # Will be calculated
                        tax_amount=Decimal("0")
                    )
                    session.add(sale)
                    await session.flush()
                    
                    # Add 2-5 items per transaction
                    num_items = random.randint(2, 5)
                    selected_items = random.sample(menu_items, min(num_items, len(menu_items)))
                    
                    transaction_total = Decimal("0")
                    
                    for item in selected_items:
                        qty = random.randint(1, 3)
                        line_total = item.price * qty
                        
                        sale_item = SaleItem(
                            tenant_id=tenant.id,
                            sale_id=sale.id,
                            menu_item_id=item.id,
                            quantity=qty,
                            unit_price_at_sale=item.price
                        )
                        session.add(sale_item)
                        transaction_total += line_total
                    
                    # Update sale total
                    sale.total_amount = transaction_total
                    sales_count += 1
            
            await session.flush()
            print(f"✅ Generated {sales_count} sales transactions")
            
            # ============ STEP 6: Generate Reviews ============
            print("\n⭐ Step 6: Creating customer reviews with sentiment...")
            
            review_count = 0
            for _ in range(25):  # Create 25 reviews
                # Weight reviews towards positive (75% positive, 15% neutral, 10% negative)
                rand = random.random()
                if rand < 0.75:
                    comment = random.choice(POSITIVE_REVIEWS)
                    sentiment = round(random.uniform(0.5, 1.0), 2)
                    rating = random.randint(4, 5)
                elif rand < 0.90:
                    comment = random.choice(NEUTRAL_REVIEWS)
                    sentiment = round(random.uniform(-0.2, 0.3), 2)
                    rating = 3
                else:
                    comment = random.choice(NEGATIVE_REVIEWS)
                    sentiment = round(random.uniform(-1.0, -0.3), 2)
                    rating = random.randint(1, 2)
                
                review_date = from_date + timedelta(days=random.randint(0, 13))
                
                review = Review(
                    tenant_id=tenant.id,
                    customer_name=f"Customer {review_count + 1}",
                    rating=rating,
                    comment=comment,
                    sentiment_score=Decimal(str(sentiment)),
                    source="internal"
                )
                session.add(review)
                review_count += 1
            
            await session.flush()
            print(f"✅ Created {review_count} customer reviews")
            
            # ============ STEP 7: Create Staff Records ============
            print("\n👥 Step 7: Creating staff records...")
            
            staff_list = []
            for name, role in STAFF_NAMES:
                staff = Staff(
                    tenant_id=tenant.id,
                    name=name,
                    role=role,
                    hourly_rate=Decimal(str(round(random.uniform(15.00, 25.00), 2))),
                    is_active=True
                )
                session.add(staff)
                await session.flush()
                staff_list.append(staff)
            
            print(f"✅ Created {len(staff_list)} staff members")
            
            # ============ STEP 8: Create Shift Records ============
            print("\n📅 Step 8: Creating shift schedules...")
            
            shift_count = 0
            for day_offset in range(14):
                shift_date = from_date + timedelta(days=day_offset)
                
                # Skip Mondays
                if shift_date.weekday() == 0:
                    continue
                
                # Create 3-5 shifts per day
                num_shifts = random.randint(3, 5)
                
                for shift_idx in range(num_shifts):
                    staff_member = random.choice(staff_list)
                    
                    # Morning, afternoon, or evening shift
                    if shift_idx == 0:
                        start_hour, duration = 10, 6  # 10 AM - 4 PM
                    elif shift_idx == 1:
                        start_hour, duration = 14, 7  # 2 PM - 9 PM
                    else:
                        start_hour, duration = 17, 6  # 5 PM - 11 PM
                    
                    shift = Shift(
                        staff_id=staff_member.id,
                        start_time=shift_date.replace(hour=start_hour, minute=0),
                        end_time=shift_date.replace(hour=(start_hour + duration) % 24, minute=0)
                    )
                    session.add(shift)
                    shift_count += 1
            
            await session.flush()
            print(f"✅ Created {shift_count} shift records")
            
            # ============ Commit All Changes ============
            print("\n💾 Committing all data to database...")
            await session.commit()
            
            # ============ SUCCESS MESSAGE ============
            print("\n" + "="*60)
            print("🎉 DATABASE SEEDING COMPLETE!")
            print("="*60)
            print(f"\n📊 Demo Data Summary:")
            print(f"   Restaurant: {RESTAURANT_NAME}")
            print(f"   Owner Email: {DEMO_EMAIL}")
            print(f"   Password: {DEMO_PASSWORD}")
            print(f"   Tenant ID: {tenant.id}")
            print(f"   Menu Items: {len(menu_items)}")
            print(f"   Sales Transactions: {sales_count}")
            print(f"   Customer Reviews: {review_count}")
            print(f"   Staff Members: {len(staff_list)}")
            print(f"   Shift Records: {shift_count}")
            print(f"\n🚀 Ready for live demo!")
            print(f"   → Start server: uvicorn app.main:app --reload")
            print(f"   → Go to http://localhost:8000/docs")
            print(f"   → Login with email: {DEMO_EMAIL}, password: {DEMO_PASSWORD}")
            print(f"   → Explore AI analytics: /analytics/daily-strategy")
            print(f"   → Check forecasts: /analytics/forecast-revenue")
            print(f"   → View recommendations: /recommendations")
            print("\n" + "="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {str(e)}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("   OpsMind AI - Database Seeding Script")
    print("   Preparing demo data for live interviews...")
    print("="*60)
    
    try:
        asyncio.run(seed_database())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
