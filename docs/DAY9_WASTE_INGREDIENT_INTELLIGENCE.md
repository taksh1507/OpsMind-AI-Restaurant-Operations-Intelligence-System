# Day 9: Waste & Ingredient Intelligence - Margin & Cost Analysis

**Week 2 Progression**: From "Looking at Sales" → "Watching the Expenses"

## Overview

Day 9 implements the **Waste & Ingredient Intelligence System**, transforming OpsMind from revenue-focused to profit-focused. While Day 8 predicted revenue, Day 9 ensures restaurants understand their actual profitability by tracking **Cost of Goods Sold (COGS)** and identifying dangerous pricing scenarios.

Most restaurant owners don't know their exact margins because ingredient costs change daily. This system automates margin analysis and alerts owners to dishes losing money after overhead costs.

---

## The Three Commits

### 🟢 Commit #1: Ingredient & Inventory Models

**Hash**: `dc1ec02`
**Message**: `feat(models): add Ingredient and Recipe association for COGS tracking`

#### What It Does
Defines the data structures needed to calculate precise cost of goods sold (COGS) for each menu item.

#### Implementation

**Location**: `app/models/menu.py`

**Two New Models**:

##### 1. Ingredient Model
```python
class Ingredient(BaseModel):
    id: int
    tenant_id: int  # Multi-tenant isolation
    name: str  # "Cheddar Cheese", "Ground Beef"
    unit: str  # "kg", "l", "pc", "g", "ml"
    unit_cost: Decimal  # Cost per unit (e.g., $12.50/kg)
```

**Attributes**:
- `name`: Ingredient name (e.g., "Cheddar Cheese")
- `unit`: Unit of measurement (kg, liters, pieces, grams, etc.)
- `unit_cost`: Cost per unit for precise calculations
- `tenant_id`: Multi-tenant isolation

**Example Usage**:
```python
# Ground Beef: $5.00 per kilogram
ingredient = Ingredient(name="Ground Beef", unit="kg", unit_cost=5.00)

# Cheddar Cheese: $12.50 per kilogram
ingredient = Ingredient(name="Cheddar Cheese", unit="kg", unit_cost=12.50)

# Lettuce: $0.75 per piece
ingredient = Ingredient(name="Lettuce", unit="pc", unit_cost=0.75)
```

##### 2. Recipe Model (Association Table)
```python
class Recipe(BaseModel):
    menu_item_id: int  # Links to MenuItem
    ingredient_id: int  # Links to Ingredient
    quantity_used: float  # Amount of ingredient in recipe
```

**Purpose**: Defines what ingredients go into each dish and how much.

**Example**:
```python
# For "Cheese Burger" (MenuItem ID = 5):
Recipe(menu_item_id=5, ingredient_id=10, quantity_used=0.2)   # 200g Ground Beef
Recipe(menu_item_id=5, ingredient_id=15, quantity_used=0.03)  # 30g Cheese
Recipe(menu_item_id=5, ingredient_id=20, quantity_used=1)     # 1 Bun

# Total COGS for Cheese Burger:
# = (0.2 kg * $5.00/kg) + (0.03 kg * $12.50/kg) + (1 * $2.00)
# = $1.00 + $0.375 + $2.00 = $3.375
```

**Key Feature**: The Recipe model includes a computed property:
```python
@property
def ingredient_cost(self) -> Decimal:
    """Total cost of this ingredient line in the recipe."""
    return self.ingredient.unit_cost * Decimal(str(self.quantity_used))
```

#### Updated MenuItem Relationship
MenuItem now has a recipes relationship:
```python
recipes = relationship("Recipe", back_populates="menu_item", cascade="all, delete-orphan")
```

This enables navigating from a menu item to all its ingredients.

#### Database Schema
```sql
-- ingredients table
CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) DEFAULT 'pc',
    unit_cost NUMERIC(10,4) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- recipes table (association table)
CREATE TABLE recipes (
    id INTEGER PRIMARY KEY,
    menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quantity_used FLOAT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

### 🔵 Commit #2: Margin Analysis Agent

**Hash**: `aede713`
**Message**: `feat(ai): implement automated profit margin auditing and risk detection`

#### What It Does
Uses AI to analyze menu item margins and identify "Danger Zones" - items priced below healthy profit levels.

#### Implementation: `check_profit_margins()`

**Location**: `app/services/ai_agent.py` (in AIConsultant class)

```python
async def check_profit_margins(
    self,
    menu_items_with_costs: list[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze menu items and identify pricing dangers."""
```

#### Key Concepts

**Healthy Margin Definition**:
- **Price-to-Cost Ratio** = Selling Price / Cost of Goods Sold
- **Healthy Ratio**: > 3.0 (price is at least 3x the cost)
- **Danger Zones**: < 3.0 (losing money after overhead)

**Example**:
```
Tuna Sandwich:
- Cost of Goods: $3.50
- Selling Price: $8.00
- Ratio: $8.00 / $3.50 = 2.29:1

⚠️ DANGER! Price is only 2.29x the cost
- This sandwich is likely losing money when overhead (labor, rent) is considered
- Recommendation: Raise to $11.20 (3.2x multiplier) for healthy margin
```

#### AI System Prompt Features

The AI system prompt teaches Gemini to:

**1. Calculate Price-to-Cost Ratios**
```
price_to_cost_ratio = selling_price / cost_of_goods
If ratio < 3.0: FLAG AS DANGER ZONE
```

**2. Assess Danger Levels**
- **Critical**: Ratio < 2.0 (severely underpriced)
- **High**: Ratio 2.0-2.5 (losing money)
- **Medium**: Ratio 2.5-3.0 (unhealthy margins)

**3. Recommend Actions**
- **Price increase**: Suggest exact new price with psychology consideration ($9.99 not $10.00)
- **Cost reduction**: Identify ingredient substitution opportunities
- **Discontinuation**: Suggest removing items if margins can't be fixed

**4. Calculate Impact**
- Estimated loss per item (considering overhead allocation)
- Monthly improvement potential from price change
- Alternative cost-reduction strategie

#### AI Output Structure
```json
{
    "risk_items": [
        {
            "item_name": "Tuna Sandwich",
            "current_price": 8.00,
            "cost_of_goods": 3.50,
            "price_to_cost_ratio": 2.29,
            "danger_level": "High",
            "estimated_loss_per_item": 1.75,
            "suggested_price": 11.20,
            "price_increase_percent": 40,
            "alternative_action": "Switch to cheaper tuna supplier"
        }
    ],
    "optimization_plan": {
        "total_items_analyzed": 25,
        "items_at_risk": 4,
        "potential_monthly_margin_improvement": 1200.00,
        "top_3_actions": [
            {
                "action": "Raise Tuna Sandwich price to $11.20",
                "expected_monthly_impact": "$350"
            }
        ]
    }
}
```

#### Fallback Logic
When Gemini is unavailable:
- Automatically identifies items with ratio < 3.0
- Suggests price multiplier of 3.2x cost
- Calculates basic opportunity estimates
- Provides reasonable defaults

#### Convenience Function
```python
async def analyze_profit_margins(
    menu_items_with_costs: list[Dict[str, Any]]
) -> Dict[str, Any]:
    """Convenience function wrapping AIConsultant.check_profit_margins()"""
    consultant = get_ai_consultant()
    return await consultant.check_profit_margins(menu_items_with_costs)
```

---

### 🟡 Commit #3: Waste Prevention API Endpoint

**Hash**: `b19cd36`
**Message**: `feat(api): expose AI-powered margin optimization and waste report`

#### What It Does
Creates a REST endpoint that gives restaurant owners a comprehensive view of their menu profitability and AI recommendations.

#### Implementation: `GET /analytics/margin-report`

**Location**: `app/api/analytics.py`

**Endpoint**:
```
GET /analytics/margin-report
```

**Authentication**: Required (JWT Bearer token)

**Response Example**:
```json
{
  "status": "success",
  "tenant_id": 123,
  "generated_at": "2026-03-28T10:30:00Z",
  "summary": {
    "total_menu_items": 25,
    "items_with_healthy_margins": 21,
    "items_in_danger_zone": 4,
    "average_margin_percent": 62.5,
    "total_revenue_from_risky_items": 450.00,
    "potential_monthly_improvement": 1200.00
  },
  "menu_items": [
    {
      "id": 5,
      "name": "Cheese Burger",
      "price": 10.50,
      "cost_of_goods": 3.375,
      "margin_percent": 67.9,
      "price_to_cost_ratio": 3.11
    },
    {
      "id": 8,
      "name": "Tuna Sandwich",
      "price": 8.00,
      "cost_of_goods": 3.50,
      "margin_percent": 56.3,
      "price_to_cost_ratio": 2.29  # DANGER!
    }
  ],
  "margin_analysis": {
    "risk_items": [ ... ],
    "optimization_plan": { ... }
  },
  "recommendations": {
    "immediate_actions": [
      {
        "action": "Review 4 menu items with margin concerns",
        "expected_monthly_impact": "$1200"
      }
    ],
    "executive_summary": "4 items identified with margin concerns..."
  },
  "action_items": [
    "Review 4 menu items with margin concerns",
    "Potential to improve margins by $1200/month",
    "Implement suggested price changes..."
  ]
}
```

#### Supporting Service: `margin_analysis.py`

**Location**: `app/services/margin_analysis.py` (new file)

**Key Functions**:

##### 1. `calculate_menu_item_cost()`
```python
async def calculate_menu_item_cost(
    session: AsyncSession,
    menu_item_id: int
) -> Decimal:
    """Calculate total COGS for a menu item by summing ingredient costs."""
    # COGS = SUM(Ingredient.unit_cost * Recipe.quantity_used)
```

**Process**:
```
Query recipes for this menu item
  ↓
For each recipe:
  - Get ingredient unit_cost
  - Multiply by quantity_used
  - Add to total
  ↓
Return total COGS
```

##### 2. `get_all_menu_items_with_costs()`
```python
async def get_all_menu_items_with_costs(
    session: AsyncSession,
    tenant_id: int
) -> List[Dict[str, Any]]:
    """Get all menu items with calculated COGS and margin info."""
```

**Returns** for each item:
```python
{
    "id": 5,
    "name": "Cheese Burger",
    "price": 10.50,
    "cost_of_goods": 3.375,
    "margin_percent": 67.9,
    "price_to_cost_ratio": 3.11
}
```

**Calculation**:
```
For each menu item:
  COGS = calculate_menu_item_cost(item_id)
  price = MenuItem.price
  margin = ((price - COGS) / price) * 100
  ratio = price / COGS
```

##### 3. `get_margin_report_summary()`
```python
async def get_margin_report_summary(
    session: AsyncSession,
    tenant_id: int
) -> Dict[str, Any]:
    """Get summary metrics for margin health assessment."""
```

**Metrics**:
- `total_items`: Total menu items
- `items_healthy`: Items with ratio > 3.0
- `items_at_risk`: Items with ratio < 3.0
- `average_margin_percent`: Mean margin across all items
- `total_revenue_at_risk`: Revenue from low-margin items
- `potential_improvement`: Estimated $ improvement if fixed

#### Endpoint Flow

```
Request: GET /analytics/margin-report
  ↓
1. Get all menu items
  ↓
2. Calculate COGS for each via recipes
  ↓
3. Compute margins and ratios
  ↓
4. Get summary metrics
  ↓
5. Call AI for optimization plan
  ↓
6. Format comprehensive response
  ↓
Response: JSON with all analysis
```

#### Error Handling

| Status | Scenario | Example |
|--------|----------|---------|
| **401** | Not authenticated | Missing JWT token |
| **404** | No menu items | Restaurant has no menu setup |
| **500** | Analysis failed | Recipe lookup error, AI error |

---

## Key Features & Metrics

### COGS Calculation
**Formula**: 
```
COGS = SUM(ingredient.unit_cost * recipe.quantity_used for each ingredient)
```

**Example** - Cheese Burger:
```
Ingredient          Unit Cost   Quantity   Line Cost
Ground Beef         $5.00/kg    0.2 kg     $1.00
Cheddar Cheese      $12.50/kg   0.03 kg    $0.375
Lettuce             $0.75/pc    1 pc       $0.75
Tomato              $1.50/pc    1 pc       $1.50
Bun                 $2.00/pc    1 pc       $2.00
                                           ─────────
                                 TOTAL      $5.625 COGS

Selling Price: $10.50
Margin: ($10.50 - $5.625) / $10.50 = 46.4%
Ratio: $10.50 / $5.625 = 1.87:1 ⚠️ DANGER!
```

### Danger Zone Detection

**3x Multiplier Rule**:
- Restaurants typically have 30-40% overhead (labor, rent, utilities)
- Items priced < 3x cost cannot absorb overhead after 20% profit
- Industry standard: healthy margin is > 65% for food items

**Risk Levels**:
| Ratio | Danger Level | Status |
|-------|--------------|--------|
| < 2.0 | 🔴 Critical | Losing money on every sale |
| 2.0-2.5 | 🟠 High | Marginal at best |
| 2.5-3.0 | 🟡 Medium | Acceptable but risky |
| > 3.0 | 🟢 Healthy | Good margin buffer |

### AI Recommendations

**Price Increase Strategy**:
- Current ratio 2.29 → Target 3.2 (provides buffer)
- Example: $8.00 → $11.20 (40% increase)
- Psychology: Suggest $10.99 instead of $11.00

**Cost Reduction Strategy**:
- Substitute cheaper ingredients (change supplier, quality)
- Reduce portion size (smaller steak cut, less sauce)
- Change preparation method (pre-made vs fresh)

**Discontinuation**:
- If margin can't be fixed and item has low sales volume
- Use that restaurant space for higher-margin items

---

## Technical Architecture

### Database Relationships

```
MenuItem (1) ──► (many) Recipe ◄─ (1) Ingredient
                    │
                    └─> Links MenuItem to Ingredients
                        with quantity used
```

### Query Example: Calculate Cheese Burger COGS

```python
# SQL equivalent
SELECT SUM(ingredients.unit_cost * recipes.quantity_used)
FROM recipes
JOIN ingredients ON recipes.ingredient_id = ingredients.id
WHERE recipes.menu_item_id = 5 AND ingredients.tenant_id = 123
```

### Multi-Tenant Isolation

**Ingredient Access**:
- Each ingredient belongs to a tenant via `tenant_id`
- Recipes link menu_items (already scoped to tenant)
- Query filters ensure data isolation

**Performance**:
- `tenant_id` indexed on ingredients table
- `menu_item_id` and `ingredient_id` indexed on recipes
- Single JOIN query per item for COGS

---

## Usage Examples

### Example 1: Get Margin Report

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/analytics/margin-report"
```

**Response includes**:
- All menu items with COGS breakdowns
- Items flagged as dangerous
- AI-generated optimization plan
- Projected monthly improvement

### Example 2: In Python

```python
from app.services.margin_analysis import get_all_menu_items_with_costs

# Get all items with costs
items = await get_all_menu_items_with_costs(session, tenant_id=123)

for item in items:
    print(f"{item['name']}: {item['price_to_cost_ratio']:.2f}:1")
    if item['price_to_cost_ratio'] < 3.0:
        print(f"  ⚠️ DANGER! Recommend price increase")
```

### Example 3: Analyze Margins with AI

```python
from app.services.ai_agent import analyze_profit_margins

# Prepare menu items with costs
menu_items = [
    {
        "id": 5,
        "name": "Cheese Burger",
        "price": 10.50,
        "cost_of_goods": 3.375,
        "margin_percent": 67.9
    },
    ...
]

# Get AI analysis
result = await analyze_profit_margins(menu_items)
print(result["analysis"]["optimization_plan"]["top_3_actions"])
```

---

## Testing Strategy

### Unit Tests
- COGS calculation accuracy
- Margin percentage computation
- Price-to-cost ratio formula
- Fallback analysis

### Integration Tests  
- Recipe creation and retrieval
- Ingredient cost updates
- Margin recalculation on cost change
- Tenant isolation

### API Tests
- Endpoint authentication
- Error handling (no items, no recipes)
- Response structure validation
- AI response parsing

---

## Next Steps (Day 10+)

### Suggested Enhancements

1. **Recipe Versioning**
   - Track ingredient cost history
   - Recalculate historical margins
   - Detect cost inflation trends

2. **Inventory Management**
   - Track ingredient stock levels
   - Predict waste based on usage
   - Auto-reorder alerts

3. **Supplier Optimization**
   - Compare ingredient costs across suppliers
   - Recommend bulk purchasing
   - Track payment terms

4. **Menu A/B Testing**
   - Test price increases on subsets
   - Measure demand elasticity
   - Optimize pricing by item

5. **Waste Tracking**
   - Log spoilage/waste amounts
   - Waste percentage by ingredient
   - Waste reduction recommendations

---

## Summary

**Day 9 successfully implements Week 2's "Watching the Expenses" foundation:**

✅ Ingredient and Recipe models for precise COGS tracking
✅ AI-powered margin analysis with danger zone detection  
✅ REST API endpoint for comprehensive margin reporting
✅ Price-to-cost ratio calculation (3x rule for health)
✅ AI optimization recommendations (price, cost, discontinuation)
✅ Multi-tenant isolation and data security

**Restaurant owners now understand**:
- Exact cost of each dish (to the penny)
- Which dishes are priced dangerously low
- Specific actions to improve profitability
- Expected monthly improvement from changes

**The magic**: Most restaurant owners don't know their exact margins because food prices change daily. OpsMind automates this completely, giving them real-time profit visibility.

**Next: Day 10 builds predictive demand forecasting based on recipes and inventory.**
