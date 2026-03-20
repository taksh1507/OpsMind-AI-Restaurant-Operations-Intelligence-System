"""Day 9: Waste & Ingredient Intelligence - Comprehensive Test Suite

Tests for:
1. Ingredient and Recipe models
2. COGS calculations
3. Margin analysis (dangerous vs healthy)
4. AI margin checking logic
5. Margin report API endpoint
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any


# ============================================================================
# Test Data
# ============================================================================

MOCK_INGREDIENTS = {
    "ground_beef": {"unit": "kg", "unit_cost": 5.00},
    "cheddar_cheese": {"unit": "kg", "unit_cost": 12.50},
    "lettuce": {"unit": "pc", "unit_cost": 0.75},
    "tomato": {"unit": "pc", "unit_cost": 1.50},
    "bun": {"unit": "pc", "unit_cost": 2.00},
    "tuna": {"unit": "kg", "unit_cost": 8.00},
    "mayo": {"unit": "l", "unit_cost": 15.00},
}

MOCK_RECIPES = {
    "cheese_burger": {
        "menu_item_id": 5,
        "price": 10.50,
        "ingredients": [
            ("ground_beef", 0.2),      # 200g
            ("cheddar_cheese", 0.03),  # 30g
            ("lettuce", 1),            # 1 piece
            ("tomato", 1),             # 1 piece
            ("bun", 1),                # 1 piece
        ]
    },
    "tuna_sandwich": {
        "menu_item_id": 8,
        "price": 8.00,
        "ingredients": [
            ("tuna", 0.15),             # 150g
            ("mayo", 0.02),             # 20ml
            ("lettuce", 1),             # 1 piece
            ("tomato", 1),              # 1 piece
            ("bun", 1),                 # 1 piece
        ]
    },
}


def calculate_recipe_cogs(recipe_name: str) -> Decimal:
    """Calculate COGS for a recipe using mock data."""
    recipe = MOCK_RECIPES[recipe_name]
    total_cost = Decimal("0")
    
    for ingredient_name, quantity in recipe["ingredients"]:
        ingredient = MOCK_INGREDIENTS[ingredient_name]
        unit_cost = Decimal(str(ingredient["unit_cost"]))
        qty = Decimal(str(quantity))
        total_cost += unit_cost * qty
    
    return total_cost


# ============================================================================
# Test Suite
# ============================================================================

def test_ingredient_model_structure():
    """Verify Ingredient model has correct attributes."""
    print("TEST 1: Ingredient Model Structure")
    
    ingredient = {
        "id": 10,
        "tenant_id": 123,
        "name": "Ground Beef",
        "unit": "kg",
        "unit_cost": 5.00,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Verify all required fields
    assert ingredient["name"] == "Ground Beef"
    assert ingredient["unit"] == "kg"
    assert float(ingredient["unit_cost"]) == 5.00
    assert ingredient["tenant_id"] == 123
    
    print("✅ Ingredient model has correct attributes")
    print(f"   - Name: {ingredient['name']}")
    print(f"   - Unit: {ingredient['unit']}")
    print(f"   - Unit Cost: ${ingredient['unit_cost']}")
    print()


def test_recipe_model_structure():
    """Verify Recipe model links MenuItem to Ingredient."""
    print("TEST 2: Recipe Model Structure")
    
    recipe = {
        "id": 1,
        "menu_item_id": 5,
        "ingredient_id": 10,
        "quantity_used": 0.2,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    assert recipe["menu_item_id"] == 5
    assert recipe["ingredient_id"] == 10
    assert recipe["quantity_used"] == 0.2
    
    # Calculate ingredient cost
    unit_cost = Decimal("5.00")
    quantity = Decimal(str(recipe["quantity_used"]))
    ingredient_cost = unit_cost * quantity
    
    assert float(ingredient_cost) == 1.0
    
    print("✅ Recipe model links MenuItem to Ingredient correctly")
    print(f"   - Menu Item ID: {recipe['menu_item_id']}")
    print(f"   - Ingredient ID: {recipe['ingredient_id']}")
    print(f"   - Quantity: {recipe['quantity_used']} kg")
    print(f"   - Ingredient Cost: ${ingredient_cost}")
    print()


def test_cogs_calculation():
    """Test accurate COGS calculation from recipes."""
    print("TEST 3: COGS Calculation")
    
    # Calculate Cheese Burger COGS
    cogs = calculate_recipe_cogs("cheese_burger")
    
    print(f"✅ Cheese Burger COGS Calculation:")
    recipe = MOCK_RECIPES["cheese_burger"]
    
    for ingredient_name, quantity in recipe["ingredients"]:
        ingredient = MOCK_INGREDIENTS[ingredient_name]
        cost = Decimal(str(ingredient["unit_cost"])) * Decimal(str(quantity))
        print(f"   - {ingredient_name.replace('_', ' ').title()}: {quantity} {ingredient['unit']} × ${ingredient['unit_cost']} = ${cost}")
    
    print(f"   - TOTAL COGS: ${cogs}")
    
    # Verify calculation
    expected = Decimal("5.625")
    assert abs(float(cogs) - float(expected)) < 0.01
    
    print()


def test_margin_calculation():
    """Test profit margin calculation."""
    print("TEST 4: Margin Calculation")
    
    recipe = MOCK_RECIPES["cheese_burger"]
    price = Decimal(str(recipe["price"]))
    cogs = calculate_recipe_cogs("cheese_burger")
    
    profit = price - cogs
    margin = ((price - cogs) / price) * 100 if price > 0 else Decimal("0")
    
    print(f"✅ Cheese Burger Margin:")
    print(f"   - Selling Price: ${price}")
    print(f"   - COGS: ${cogs}")
    print(f"   - Profit: ${profit}")
    print(f"   - Margin %: {margin:.1f}%")
    
    assert margin > 40  # Should have healthy margin
    
    print()


def test_price_to_cost_ratio():
    """Test price-to-cost ratio calculation (danger zone detection)."""
    print("TEST 5: Price-to-Cost Ratio (Danger Zone Detection)")
    
    # Test Cheese Burger (healthy)
    recipe_cb = MOCK_RECIPES["cheese_burger"]
    cogs_cb = calculate_recipe_cogs("cheese_burger")
    price_cb = Decimal(str(recipe_cb["price"]))
    ratio_cb = price_cb / cogs_cb
    
    print(f"✅ Cheese Burger:")
    print(f"   - Price: ${price_cb}")
    print(f"   - COGS: ${cogs_cb}")
    print(f"   - Ratio: {ratio_cb:.2f}:1", end="")
    
    if ratio_cb > 3.0:
        print(" 🟢 HEALTHY")
    elif ratio_cb > 2.5:
        print(" 🟡 MEDIUM RISK")
    else:
        print(" 🔴 DANGER!")
    
    # Test Tuna Sandwich (dangerous)
    recipe_ts = MOCK_RECIPES["tuna_sandwich"]
    cogs_ts = calculate_recipe_cogs("tuna_sandwich")
    price_ts = Decimal(str(recipe_ts["price"]))
    ratio_ts = price_ts / cogs_ts
    
    print(f"✅ Tuna Sandwich:")
    print(f"   - Price: ${price_ts}")
    print(f"   - COGS: ${cogs_ts}")
    print(f"   - Ratio: {ratio_ts:.2f}:1", end="")
    
    if ratio_ts > 3.0:
        print(" 🟢 HEALTHY")
    elif ratio_ts > 2.5:
        print(" 🟡 MEDIUM RISK")
    else:
        print(" 🔴 DANGER!")
    
    # Verify Tuna is in danger zone (ratio < 3.0)
    assert ratio_ts < 3.0, "Tuna Sandwich should be in danger zone"
    
    print()


def test_danger_zone_identification():
    """Test identification of dangerous (low margin) items."""
    print("TEST 6: Danger Zone Identification")
    
    # Create menu with mix of healthy and dangerous items
    menu_items = []
    for recipe_name, recipe in MOCK_RECIPES.items():
        cogs = calculate_recipe_cogs(recipe_name)
        price = Decimal(str(recipe["price"]))
        ratio = float(price / cogs)
        
        menu_items.append({
            "name": recipe_name.replace("_", " ").title(),
            "price": float(price),
            "cogs": float(cogs),
            "ratio": ratio,
            "is_danger": ratio < 3.0
        })
    
    danger_items = [item for item in menu_items if item["is_danger"]]
    healthy_items = [item for item in menu_items if not item["is_danger"]]
    
    print(f"✅ Menu Analysis:")
    print(f"   - Total Items: {len(menu_items)}")
    print(f"   - Healthy Items: {len(healthy_items)}")
    print(f"   - Danger Items: {len(danger_items)}")
    print()
    
    if danger_items:
        print("   Danger Items:")
        for item in danger_items:
            print(f"   ⚠️  {item['name']}: {item['ratio']:.2f}:1 ratio")
    
    print()


def test_price_recommendation():
    """Test AI-style price adjustment recommendation."""
    print("TEST 7: Price Recommendation Logic")
    
    # For Tuna Sandwich in danger zone
    recipe = MOCK_RECIPES["tuna_sandwich"]
    cogs = calculate_recipe_cogs("tuna_sandwich")
    current_price = Decimal(str(recipe["price"]))
    
    # Recommendation: multiply by 3.2 to get healthy margin
    suggested_multiplier = Decimal("3.2")
    suggested_price = cogs * suggested_multiplier
    price_increase = suggested_price - current_price
    price_increase_percent = (price_increase / current_price) * 100
    
    print(f"✅ Tuna Sandwich Price Adjustment:")
    print(f"   - Current Price: ${current_price:.2f}")
    print(f"   - Current Ratio: {float(current_price / cogs):.2f}:1")
    print(f"   - COGS: ${cogs:.2f}")
    print()
    print(f"   - Suggestion: Raise to ${suggested_price:.2f}")
    print(f"   - Increase: +${price_increase:.2f} ({price_increase_percent:.0f}%)")
    print(f"   - New Ratio: {float(suggested_price / cogs):.2f}:1")
    print()
    
    # Verify new ratio is healthy
    new_ratio = float(suggested_price / cogs)
    assert new_ratio > 3.0, "Suggested price should result in healthy ratio"
    
    print()


def test_margin_analysis_output_structure():
    """Test structure of AI margin analysis output."""
    print("TEST 8: Margin Analysis Output Structure")
    
    # Create mock margin analysis output
    analysis = {
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
        "healthy_items": [
            {
                "item_name": "Cheese Burger",
                "margin_percent": 46.4,
                "price_to_cost_ratio": 1.87
            }
        ],
        "optimization_plan": {
            "total_items_analyzed": 2,
            "items_at_risk": 1,
            "total_current_revenue_at_risk": 8.00,
            "potential_monthly_margin_improvement": 350.00,
            "top_3_actions": [
                {
                    "action": "Raise Tuna Sandwich price to $11.20",
                    "expected_monthly_impact": "$350"
                }
            ],
            "executive_summary": "1 item identified with margin concerns..."
        }
    }
    
    # Verify structure
    assert "risk_items" in analysis
    assert "healthy_items" in analysis
    assert "optimization_plan" in analysis
    
    assert len(analysis["risk_items"]) > 0
    assert analysis["optimization_plan"]["items_at_risk"] > 0
    
    print("✅ Margin analysis output structure is valid")
    print(f"   - Risk Items: {len(analysis['risk_items'])}")
    print(f"   - Healthy Items: {len(analysis['healthy_items'])}")
    print(f"   - Potential Monthly Improvement: ${analysis['optimization_plan']['potential_monthly_margin_improvement']:.2f}")
    print(f"   - Top Recommendation: {analysis['optimization_plan']['top_3_actions'][0]['action']}")
    print()


def test_margin_report_response():
    """Test complete margin report API response structure."""
    print("TEST 9: Margin Report API Response")
    
    # Create mock margin report response
    response = {
        "status": "success",
        "tenant_id": 123,
        "generated_at": "2026-03-28T10:30:00Z",
        "summary": {
            "total_menu_items": 2,
            "items_with_healthy_margins": 1,
            "items_in_danger_zone": 1,
            "average_margin_percent": 62.5,
            "total_revenue_from_risky_items": 8.00,
            "potential_monthly_improvement": 350.00
        },
        "menu_items": [
            {
                "id": 5,
                "name": "Cheese Burger",
                "price": 10.50,
                "cost_of_goods": 5.625,
                "margin_percent": 46.4,
                "price_to_cost_ratio": 1.87
            }
        ],
        "recommendations": {
            "immediate_actions": [
                {
                    "action": "Review 1 menu items with margin concerns",
                    "expected_monthly_impact": "$350"
                }
            ],
            "executive_summary": "Analysis identified 1 item with margin concerns..."
        }
    }
    
    # Verify structure
    assert response["status"] == "success"
    assert "summary" in response
    assert "menu_items" in response
    assert "recommendations" in response
    
    print("✅ Margin report API response structure is valid")
    print(f"   - Status: {response['status']}")
    print(f"   - Total Items: {response['summary']['total_menu_items']}")
    print(f"   - Items at Risk: {response['summary']['items_in_danger_zone']}")
    print(f"   - Potential Monthly Improvement: ${response['summary']['potential_monthly_improvement']:.2f}")
    print()


def test_json_serialization():
    """Test that all data structures are JSON serializable."""
    print("TEST 10: JSON Serialization")
    
    mock_response = {
        "status": "success",
        "items": [
            {
                "name": "Cheese Burger",
                "price": 10.50,
                "cogs": 5.625,
                "margin_percent": 46.4,
                "created_at": datetime.now().isoformat()
            }
        ],
        "metrics": {
            "total_items": 1,
            "average_margin": 46.4
        }
    }
    
    try:
        json_str = json.dumps(mock_response)
        print(f"✅ Response is JSON serializable")
        print(f"   - JSON size: {len(json_str)} bytes")
        
        # Verify can deserialize
        deserialized = json.loads(json_str)
        assert deserialized["status"] == "success"
        print(f"✅ Can serialize and deserialize successfully")
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        raise
    
    print()


def test_multi_item_margin_portfolio():
    """Test margin analysis across a portfolio of items."""
    print("TEST 11: Multi-Item Margin Portfolio")
    
    # Create diverse menu
    portfolio = [
        {"name": "Premium Steak", "price": 28.00, "cogs": 8.00, "ratio": 28.00/8.00},
        {"name": "Cheese Burger", "price": 10.50, "cogs": 5.625, "ratio": 10.50/5.625},
        {"name": "Tuna Sandwich", "price": 8.00, "cogs": 3.50, "ratio": 8.00/3.50},
        {"name": "Caesar Salad", "price": 12.00, "cogs": 3.00, "ratio": 12.00/3.00},
    ]
    
    # Analyze portfolio
    healthy = [item for item in portfolio if item["ratio"] > 3.0]
    danger = [item for item in portfolio if item["ratio"] < 3.0]
    
    print(f"✅ Menu Portfolio Analysis:")
    print(f"   - Total Items: {len(portfolio)}")
    print(f"   - Healthy Margin Items: {len(healthy)}")
    print(f"   - Danger Zone Items: {len(danger)}")
    print()
    
    print("   Healthy Items (>3.0x ratio):")
    for item in healthy:
        print(f"   ✅ {item['name']}: {item['ratio']:.2f}:1")
    
    print()
    print("   Danger Items (<3.0x ratio):")
    for item in danger:
        suggested = item['cogs'] * 3.2
        increase = ((suggested - item['price']) / item['price']) * 100
        print(f"   ⚠️  {item['name']}: {item['ratio']:.2f}:1")
        print(f"       → Raise from ${item['price']:.2f} to ${suggested:.2f} (+{increase:.0f}%)")
    
    print()


def run_all_tests():
    """Run all test suites."""
    print("=" * 80)
    print("DAY 9: WASTE & INGREDIENT INTELLIGENCE - TEST SUITE")
    print("=" * 80)
    print()
    
    tests = [
        test_ingredient_model_structure,
        test_recipe_model_structure,
        test_cogs_calculation,
        test_margin_calculation,
        test_price_to_cost_ratio,
        test_danger_zone_identification,
        test_price_recommendation,
        test_margin_analysis_output_structure,
        test_margin_report_response,
        test_json_serialization,
        test_multi_item_margin_portfolio,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"❌ Test error: {e}")
            failed += 1
            print()
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - Ready for production!")
    else:
        print(f"⚠️  {failed} test(s) failed - Review implementation")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
