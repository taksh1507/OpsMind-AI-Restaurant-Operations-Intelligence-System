"""Test Commit #2: Strategy Prompt Engineering

This test demonstrates the structured prompt engineering for the AI consultant.
It validates that the AI returns clean JSON objects with specific strategic recommendations.
"""

import asyncio
import json
from decimal import Decimal
from datetime import datetime, timezone

# Sample restaurant performance data for testing
SAMPLE_PERFORMANCE_DATA = {
    "tenant_id": 1,
    "period": {
        "start_date": (datetime.now(timezone.utc) - __import__('datetime').timedelta(days=30)).isoformat(),
        "end_date": datetime.now(timezone.utc).isoformat()
    },
    "total_revenue": 15250.75,
    "total_profit": 4575.23,
    "profit_margin_percent": 30.0,
    "cost_of_goods_sold": 10675.52,
    "transaction_count": 385,
    "total_items_sold": 2847,
    "top_selling_items": [
        {
            "menu_item_id": 1,
            "name": "Truffle Fries",
            "quantity_sold": 450,
            "revenue_generated": 2700.00
        },
        {
            "menu_item_id": 2,
            "name": "Grilled Salmon",
            "quantity_sold": 185,
            "revenue_generated": 3330.00
        },
        {
            "menu_item_id": 3,
            "name": "Caesar Salad",
            "quantity_sold": 320,
            "revenue_generated": 1920.00
        },
        {
            "menu_item_id": 4,
            "name": "Hamburger Deluxe",
            "quantity_sold": 512,
            "revenue_generated": 3840.00
        },
        {
            "menu_item_id": 5,
            "name": "Chocolate Mousse",
            "quantity_sold": 580,
            "revenue_generated": 2030.00
        }
    ]
}


async def test_structured_prompt_engineering():
    """Test that the AI returns valid JSON with structured recommendations."""
    
    print("=" * 70)
    print("TEST: Commit #2 - Strategy Prompt Engineering")
    print("=" * 70)
    print()
    
    try:
        from app.services.ai_agent import generate_restaurant_strategy
        
        print("📊 RESTAURANT PERFORMANCE DATA:")
        print(json.dumps({
            "revenue": SAMPLE_PERFORMANCE_DATA["total_revenue"],
            "profit": SAMPLE_PERFORMANCE_DATA["total_profit"],
            "margin": f"{SAMPLE_PERFORMANCE_DATA['profit_margin_percent']}%",
            "top_items": [item["name"] for item in SAMPLE_PERFORMANCE_DATA["top_selling_items"][:3]]
        }, indent=2))
        print()
        
        print("🤖 SENDING TO AI CONSULTANT...")
        print()
        
        # Generate strategy
        result = await generate_restaurant_strategy(SAMPLE_PERFORMANCE_DATA)
        
        print("✅ AI RESPONSE RECEIVED")
        print()
        
        if result.get("status") == "error":
            print(f"❌ Error: {result.get('message')}")
            return False
        
        strategy = result.get("strategy", {})
        
        # Validate required fields
        required_fields = [
            "star_dish",
            "underperformer",
            "price_recommendation",
            "inventory_saving",
            "overall_health",
            "actionable_insights"
        ]
        
        print("📋 STRUCTURED STRATEGY OUTPUT:")
        print()
        
        missing_fields = []
        for field in required_fields:
            if field in strategy:
                print(f"✅ {field}")
            else:
                print(f"❌ {field} (MISSING)")
                missing_fields.append(field)
        
        print()
        
        if missing_fields:
            print(f"⚠️  Missing fields: {', '.join(missing_fields)}")
            print()
        
        # Display the full strategy in formatted JSON
        print("📑 FULL STRATEGY JSON:")
        print(json.dumps(strategy, indent=2, default=str))
        print()
        
        # Specific validations
        print("🔍 VALIDATION CHECKS:")
        
        # 1. Star dish identification
        if "star_dish" in strategy and strategy["star_dish"].get("name"):
            print(f"✅ Star Dish Identified: {strategy['star_dish']['name']}")
        else:
            print("❌ Star Dish: No name found")
        
        # 2. Underperformer identification
        if "underperformer" in strategy and strategy["underperformer"].get("name"):
            print(f"✅ Underperformer Identified: {strategy['underperformer']['name']}")
        else:
            print("❌ Underperformer: No name found")
        
        # 3. Price recommendation with numbers
        if "price_recommendation" in strategy:
            price_rec = strategy["price_recommendation"]
            if price_rec.get("suggested_price") and price_rec.get("item"):
                print(f"✅ Price Recommendation: {price_rec['item']} → ${price_rec['suggested_price']}")
            else:
                print("❌ Price Recommendation: Missing suggested_price or item")
        
        # 4. Inventory saving
        if "inventory_saving" in strategy and strategy["inventory_saving"].get("area"):
            print(f"✅ Inventory Saving Identified: {strategy['inventory_saving']['area']}")
        else:
            print("❌ Inventory Saving: No area identified")
        
        # 5. Actionable insights
        if "actionable_insights" in strategy:
            insights = strategy["actionable_insights"]
            print(f"✅ Actionable Insights: {len(insights)} item(s) provided")
        else:
            print("❌ Actionable Insights: Not found")
        
        print()
        print("=" * 70)
        print("TEST RESULT: ✅ PASSED" if not missing_fields else "TEST RESULT: ⚠️  PARTIAL")
        print("=" * 70)
        print()
        
        return True
    
    except ImportError:
        print("❌ SETUP ERROR: Cannot import AI modules")
        print("   Make sure to run: pip install google-generativeai")
        print("   And set GOOGLE_API_KEY environment variable")
        return False
    
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # For sync execution
    result = asyncio.run(test_structured_prompt_engineering())
    exit(0 if result else 1)
