"""Day 9: API Endpoint Testing Guide

This module provides examples and test cases for the margin-report endpoint.
Uses FastAPI TestClient for HTTP testing.
"""

# ============================================================================
# Example API Tests (for manual testing or pytest integration)
# ============================================================================

ENDPOINT_TESTS = {
    "success": {
        "description": "GET /analytics/margin-report - Success with data",
        "method": "GET",
        "endpoint": "/analytics/margin-report",
        "auth": "Required (Bearer token)",
        "status_code": 200,
        "response_example": {
            "status": "success",
            "tenant_id": 123,
            "generated_at": "2026-03-28T10:30:00Z",
            "summary": {
                "total_menu_items": 2,
                "items_with_healthy_margins": 1,
                "items_in_danger_zone": 1,
                "average_margin_percent": 64.2,
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
                },
                {
                    "id": 8,
                    "name": "Tuna Sandwich",
                    "price": 8.00,
                    "cost_of_goods": 5.75,
                    "margin_percent": 28.1,
                    "price_to_cost_ratio": 1.39
                }
            ],
            "margin_analysis": {
                "risk_items": [
                    {
                        "item_name": "Tuna Sandwich",
                        "current_price": 8.00,
                        "cost_of_goods": 5.75,
                        "price_to_cost_ratio": 1.39,
                        "danger_level": "High",
                        "estimated_loss_per_item": 1.75,
                        "suggested_price": 18.40,
                        "price_increase_percent": 130,
                        "alternative_action": "Negotiate better tuna supplier rates"
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
                            "action": "Adjust pricing on 1 high-risk item to 3.2x COGS",
                            "expected_monthly_impact": "$350"
                        }
                    ],
                    "executive_summary": "1 item identified with margin concerns. "
                                        "If prices adjusted to healthy levels, potential "
                                        "monthly margin improvement: $350"
                }
            },
            "recommendations": {
                "immediate_actions": [
                    {
                        "action": "Review Tuna Sandwich pricing (1.39:1 ratio)",
                        "expected_monthly_impact": "$350"
                    }
                ],
                "executive_summary": "Analysis identified 1 item currently priced below optimal levels. "
                                    "Strategic pricing adjustment could improve monthly margin by $350."
            }
        }
    },
    
    "no_menu_items": {
        "description": "GET /analytics/margin-report - No menu items",
        "method": "GET",
        "endpoint": "/analytics/margin-report",
        "auth": "Required (Bearer token)",
        "status_code": 404,
        "response_example": {
            "detail": "No menu items found for this restaurant"
        }
    },
    
    "no_auth": {
        "description": "GET /analytics/margin-report - Missing authentication",
        "method": "GET",
        "endpoint": "/analytics/margin-report",
        "auth": "None (missing)",
        "status_code": 401,
        "response_example": {
            "detail": "Not authenticated"
        }
    },
    
    "invalid_token": {
        "description": "GET /analytics/margin-report - Invalid token",
        "method": "GET",
        "endpoint": "/analytics/margin-report",
        "auth": "Bearer invalid_token_123",
        "status_code": 401,
        "response_example": {
            "detail": "Invalid token"
        }
    },
    
    "ai_analysis_failure": {
        "description": "GET /analytics/margin-report - AI service unavailable",
        "method": "GET",
        "endpoint": "/analytics/margin-report",
        "auth": "Required (Bearer token)",
        "status_code": 200,
        "note": "Returns fallback margin analysis without AI recommendations",
        "response_example": {
            "status": "success",
            "tenant_id": 123,
            "summary": {
                "total_menu_items": 2,
                "items_with_healthy_margins": 1,
                "items_in_danger_zone": 1,
                "average_margin_percent": 64.2,
                "total_revenue_from_risky_items": 8.00,
                "potential_monthly_improvement": 350.00
            },
            "menu_items": [
                # ... menu items ...
            ],
            "margin_analysis": {
                "risk_items": [
                    # ... basic analysis without AI recommendations ...
                ],
                "optimization_plan": {
                    "total_items_analyzed": 2,
                    "items_at_risk": 1,
                    "total_current_revenue_at_risk": 8.00,
                    "potential_monthly_margin_improvement": 350.00,
                    "executive_summary": "Analysis completed using fallback logic. "
                                        "AI service temporarily unavailable. "
                                        "Recommendations generated using standard margins calculation."
                }
            }
        }
    }
}


# ============================================================================
# Manual Testing Guide
# ============================================================================

TESTING_GUIDE = """
## Manual Testing Guide - Margin Report API

### Prerequisites
1. Start the FastAPI server:
   ```bash
   cd app
   python -m uvicorn main:app --reload
   ```

2. Get a valid authentication token:
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{"email": "admin@restaurant.com", "password": "password"}'
   ```
   Save the access_token from response.

### Test 1: Successful Margin Report Request
```bash
TENANT_ID="123"
TOKEN="<your_access_token>"

curl -X GET "http://localhost:8000/analytics/margin-report" \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" | jq .

# Expected: 200 OK with full margin analysis
```

### Test 2: Missing Authorization
```bash
curl -X GET "http://localhost:8000/analytics/margin-report" \\
  -H "Content-Type: application/json"

# Expected: 401 {"detail": "Not authenticated"}
```

### Test 3: No Menu Items (Empty Restaurant)
```bash
# First, ensure no menu items exist for this tenant
curl -X GET "http://localhost:8000/analytics/margin-report" \\
  -H "Authorization: Bearer $TOKEN"

# Expected: 404 {"detail": "No menu items found for this restaurant"}
```

### Test 4: Multiple Items Analysis
```bash
# Create 5 menu items with different prices and costs
for i in {1..5}; do
  curl -X POST "http://localhost:8000/menu-items" \\
    -H "Authorization: Bearer $TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{
      "name": "Item '$i'",
      "description": "Test item '$i'",
      "price": '$((10 + i * 5))',
      "status": "available"
    }'
done

# Then request margin report
curl -X GET "http://localhost:8000/analytics/margin-report" \\
  -H "Authorization: Bearer $TOKEN" | jq '.summary'

# Expected: summary with stats for all 5 items
```

### Test 5: JSON Response Validation
```bash
TOKEN="<your_access_token>"

response=$(curl -s -X GET "http://localhost:8000/analytics/margin-report" \\
  -H "Authorization: Bearer $TOKEN")

# Verify response has all required fields
echo "$response" | jq '.status'                    # Should: "success"
echo "$response" | jq '.summary.total_menu_items'  # Should: number > 0
echo "$response" | jq '.menu_items | length'       # Should: match summary
echo "$response" | jq '.margin_analysis'           # Should: object with risk_items
echo "$response" | jq '.recommendations'           # Should: object with actions
```

## Automated Testing with TestClient

### Example Test Code
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth_token():
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password"
    })
    return response.json()["access_token"]

def test_margin_report_success():
    token = get_auth_token()
    response = client.get(
        "/analytics/margin-report",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "summary" in data
    assert "menu_items" in data
    assert "margin_analysis" in data
    assert "recommendations" in data
    
    # Verify summary matches menu_items count
    summary_count = data["summary"]["total_menu_items"]
    items_count = len(data["menu_items"])
    assert summary_count == items_count

def test_margin_report_no_auth():
    response = client.get("/analytics/margin-report")
    assert response.status_code == 401

def test_margin_report_no_items():
    # After deleting all menu items
    token = get_auth_token()
    response = client.get(
        "/analytics/margin-report",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
```

## Performance Testing

### Load Test - 100 Requests
```bash
TOKEN="<your_access_token>"
ENDPOINT="http://localhost:8000/analytics/margin-report"

# Using Apache Bench
ab -n 100 -c 10 \\
   -H "Authorization: Bearer $TOKEN" \\
   $ENDPOINT

# Expected: All requests complete in < 5 seconds
# Expected: No errors (5xx status codes)
```

### Load Test - Concurrent Margin Analysis
```bash
# 20 concurrent requests
TOKEN="<your_access_token>"
ENDPOINT="http://localhost:8000/analytics/margin-report"

for i in {1..20}; do
  curl -X GET "$ENDPOINT" \\
    -H "Authorization: Bearer $TOKEN" \\
    &
done

wait

# All requests should complete successfully
```

## Data Validation Checklist

After calling `/analytics/margin-report`:

- [ ] Response status code is 200
- [ ] Response has "status": "success"
- [ ] "summary" object exists with:
  - [ ] total_menu_items (integer > 0)
  - [ ] items_with_healthy_margins (integer >= 0)
  - [ ] items_in_danger_zone (integer >= 0)
  - [ ] average_margin_percent (float 0-100)
  - [ ] total_revenue_from_risky_items (float >= 0)
  - [ ] potential_monthly_improvement (float >= 0)
- [ ] "menu_items" array matches summary count:
  - [ ] Each item has id, name, price, cost_of_goods, margin_percent, price_to_cost_ratio
  - [ ] All prices > 0
  - [ ] All COGS >= 0
  - [ ] margin_percent = (price - cogs) / price * 100
  - [ ] price_to_cost_ratio = price / cogs
- [ ] "margin_analysis" object contains:
  - [ ] risk_items array (items with ratio < 3.0)
  - [ ] healthy_items array (items with ratio >= 3.0)
  - [ ] optimization_plan object
- [ ] "recommendations" object contains:
  - [ ] immediate_actions array
  - [ ] executive_summary string

## Troubleshooting

### Response is empty or null
**Cause:** No menu items exist for tenant
**Solution:** Create menu items first, then request report

### Status 500 error
**Cause:** Database connection failed or AI service error
**Solution:** Check app logs, verify database is running, check Gemini API key

### Recommendation count mismatches
**Cause:** COGS calculation error
**Solution:** Verify ingredients exist, recipe associations are correct

### Response takes > 5 seconds
**Cause:** Too many menu items or Gemini API slow
**Solution:** Optimize database query, add caching layer

## Integration with Monitoring

### Alert if Analysis Fails
```python
# In monitoring/alerting.py
response = requests.get(
    "https://api.yourrestaurant.com/analytics/margin-report",
    headers={"Authorization": f"Bearer {api_token}"}
)

if response.status_code != 200:
    send_alert(f"Margin analysis failed: {response.status_code}")
```

### Track Margin Improvements
```python
# Store margin report in analytics database
historical_margins.insert({
    "date": datetime.now(),
    "average_margin": response.json()["summary"]["average_margin_percent"],
    "items_at_risk": response.json()["summary"]["items_in_danger_zone"],
    "potential_improvement": response.json()["summary"]["potential_monthly_improvement"]
})
```
"""


# ============================================================================
# Response Schema Reference
# ============================================================================

RESPONSE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["status", "tenant_id", "summary", "menu_items", "margin_analysis", "recommendations"],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["success", "error"],
            "description": "Status of the margin analysis"
        },
        "tenant_id": {
            "type": "integer",
            "description": "Restaurant/tenant ID"
        },
        "generated_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO 8601 timestamp when report was generated"
        },
        "summary": {
            "type": "object",
            "required": [
                "total_menu_items",
                "items_with_healthy_margins",
                "items_in_danger_zone",
                "average_margin_percent",
                "total_revenue_from_risky_items",
                "potential_monthly_improvement"
            ],
            "properties": {
                "total_menu_items": {"type": "integer", "minimum": 0},
                "items_with_healthy_margins": {"type": "integer", "minimum": 0},
                "items_in_danger_zone": {"type": "integer", "minimum": 0},
                "average_margin_percent": {"type": "number", "minimum": 0, "maximum": 100},
                "total_revenue_from_risky_items": {"type": "number", "minimum": 0},
                "potential_monthly_improvement": {"type": "number", "minimum": 0}
            }
        },
        "menu_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "price": {"type": "number", "minimum": 0},
                    "cost_of_goods": {"type": "number", "minimum": 0},
                    "margin_percent": {"type": "number"},
                    "price_to_cost_ratio": {"type": "number", "minimum": 0}
                }
            }
        },
        "margin_analysis": {
            "type": "object",
            "properties": {
                "risk_items": {"type": "array"},
                "healthy_items": {"type": "array"},
                "optimization_plan": {
                    "type": "object",
                    "properties": {
                        "total_items_analyzed": {"type": "integer"},
                        "items_at_risk": {"type": "integer"},
                        "total_current_revenue_at_risk": {"type": "number"},
                        "potential_monthly_margin_improvement": {"type": "number"},
                        "executive_summary": {"type": "string"}
                    }
                }
            }
        },
        "recommendations": {
            "type": "object",
            "properties": {
                "immediate_actions": {"type": "array"},
                "executive_summary": {"type": "string"}
            }
        }
    }
}


if __name__ == "__main__":
    print("=" * 80)
    print("DAY 9: API ENDPOINT TESTING GUIDE")
    print("=" * 80)
    print()
    print("Quick Start:")
    print()
    print("1. Review test cases:")
    for key, test in ENDPOINT_TESTS.items():
        print(f"   - {key}: {test['description']}")
    print()
    print("2. Follow manual testing guide above")
    print("3. Integrate automated tests in CI/CD")
    print()
    print("See comments in this file for:")
    print("  - curl command examples")
    print("  - pytest test code")
    print("  - Load testing procedures")
    print("  - Response validation checklist")
    print()
