# OpsMind AI - API Reference Documentation

## Table of Contents
1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Error Handling](#error-handling)
5. [Request/Response Examples](#requestresponse-examples)

---

## API Overview

**Base URL**: `http://localhost:8000/api/v1`  
**API Version**: 1.0  
**Authentication**: JWT (Bearer token)  
**Response Format**: JSON  
**Content-Type**: `application/json`

### Rate Limiting
- No hard limits enforced (consider implementing in production)
- Gemini API quota: Optimized with caching layer

---

## Authentication

### Register New User
```http
POST /auth/register

Content-Type: application/json

{
  "email": "owner@restaurant.com",
  "password": "secure_password_123",
  "restaurant_name": "Taj Cuisine"
}
```

**Response (201 Created)**
```json
{
  "id": 1,
  "email": "owner@restaurant.com",
  "tenant_id": 1,
  "role": "owner",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Login
```http
POST /auth/login

Content-Type: application/x-www-form-urlencoded

email=owner@restaurant.com&password=secure_password_123
```

**Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Token Structure (JWT)
```
Header: {
  "alg": "HS256",
  "typ": "JWT"
}

Payload: {
  "sub": "owner@restaurant.com",
  "tenant_id": 1,
  "role": "owner",
  "exp": 1713024000,
  "iat": 1713020400
}

Signature: HMAC-SHA256(secret)
```

### Request Headers
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

---

## Endpoints

### 1. Customer Intelligence (Day 24)

#### Get Customer Briefing
```http
GET /customers/{id}/briefing

Authorization: Bearer {token}
```

**Parameters**:
- `id` (path, required): Customer ID

**Response (200 OK)**
```json
{
  "status": "success",
  "customer_id": 1,
  "customer_name": "Raj Verma",
  "total_visits": 5,
  "cheat_sheet": [
    "👤 LTV: ₹5,400.00",
    "🍽️ Favorite: Paneer Chilly",
    "🤖 AI: [High-Value Regular] Offer sample of new Malai Kofta..."
  ],
  "persona": "High-Value Regular",
  "ltv": 5400.00,
  "favorite_item": "Paneer Chilly",
  "suggested_action": "Offer sample of new Malai Kofta",
  "preferences": {
    "favorite_items": ["Paneer Chilly", "Butter Chicken"],
    "spice_level": "very spicy",
    "allergies": ["peanuts"]
  },
  "order_history_sample": [...]
}
```

---

### 2. Menu Management

#### List All Menu Items
```http
GET /menu

Authorization: Bearer {token}

Query Parameters:
?category_id=1&limit=20&offset=0
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Paneer Chilly",
      "description": "Crispy paneer with chilly sauce",
      "price": 280.00,
      "cost_of_goods": 84.00,
      "margin_percent": 70.0,
      "category_id": 1,
      "category_name": "Appetizers",
      "is_active": true,
      "created_at": "2026-03-15T10:30:00Z"
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

#### Create Menu Item
```http
POST /menu

Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Malai Kofta",
  "description": "Soft cottage cheese balls in cream sauce",
  "price": 320.00,
  "cost_of_goods": 96.00,
  "category_id": 2
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "id": 2,
    "name": "Malai Kofta",
    "price": 320.00,
    "cost_of_goods": 96.00,
    "margin_percent": 70.0,
    "is_active": true
  }
}
```

---

### 3. Sales & Transactions

#### Record Sale
```http
POST /sales

Authorization: Bearer {token}
Content-Type: application/json

{
  "total_amount": 580.00,
  "tax_amount": 104.40,
  "payment_method": "card",
  "items": [
    {"menu_item_id": 1, "quantity": 2, "unit_price_at_sale": 280.00},
    {"menu_item_id": 2, "quantity": 1, "unit_price_at_sale": 320.00}
  ]
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "total_amount": 580.00,
    "tax_amount": 104.40,
    "grand_total": 684.40,
    "payment_method": "card",
    "item_count": 3,
    "timestamp": "2026-04-13T10:30:00Z"
  }
}
```

#### Get Sales History
```http
GET /sales

Authorization: Bearer {token}

Query Parameters:
?start_date=2026-04-01&end_date=2026-04-13&limit=50
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "total_amount": 580.00,
      "grand_total": 684.40,
      "payment_method": "card",
      "item_count": 3,
      "timestamp": "2026-04-13T10:30:00Z"
    }
  ],
  "total": 156,
  "period": {
    "start": "2026-04-01",
    "end": "2026-04-13",
    "days": 13
  }
}
```

---

### 4. Analytics & AI Insights

#### Get Overall Analytics
```http
GET /analytics

Authorization: Bearer {token}

Query Parameters:
?start_date=2026-03-15&end_date=2026-04-13
```

**Response (200 OK)**
```json
{
  "status": "success",
  "summary": {
    "total_revenue": 45000.00,
    "total_profit": 13500.00,
    "profit_margin_percent": 30.0,
    "transaction_count": 156,
    "total_items_sold": 487
  },
  "top_selling_items": [
    {"name": "Paneer Chilly", "quantity": 120, "revenue": 8400.00},
    {"name": "Butter Chicken", "quantity": 95, "revenue": 9500.00}
  ],
  "period": {
    "start_date": "2026-03-15",
    "end_date": "2026-04-13"
  }
}
```

#### Get AI Strategy Briefing
```http
GET /analytics/ai-briefing

Authorization: Bearer {token}

Query Parameters (optional):
?start_date=2026-03-15&end_date=2026-04-13
```

**Response (200 OK)**
```json
{
  "status": "success",
  "tenant_id": 1,
  "briefing": {
    "star_dish": {
      "name": "Paneer Chilly",
      "quantity_sold": 120,
      "revenue_generated": 8400.00,
      "profit_contribution": 2520.00,
      "reason": "Highest revenue generator with strong margins"
    },
    "underperformer": {
      "name": "Chocolate Mousse",
      "quantity_sold": 45,
      "margin_percent": 25.0,
      "problem": "High volume but thin margins"
    },
    "price_recommendation": {
      "item": "Paneer Chilly",
      "current_price": 280.00,
      "suggested_price": 302.00,
      "price_change_percent": 8.0,
      "expected_weekly_impact": "+₹540 if demand stable"
    },
    "inventory_saving": {
      "area": "Waste reduction audit",
      "estimated_monthly_savings": "₹300-500"
    },
    "overall_health": {
      "rating": "Good",
      "current_margin_percent": 30.0,
      "margin_target": 35.0,
      "key_finding": "Room for 5% margin improvement"
    },
    "top_priorities": [
      {
        "priority": 1,
        "action": "Test +8% price on Paneer Chilly",
        "expected_result": "+₹400-600 weekly profit impact"
      }
    ]
  },
  "data_period": {
    "start_date": "2026-03-15T00:00:00Z",
    "end_date": "2026-04-13T23:59:59Z"
  }
}
```

#### Get Revenue Forecast
```http
GET /analytics/revenue-forecast

Authorization: Bearer {token}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "forecast": {
    "next_day_1_revenue": 2850.00,
    "next_day_2_revenue": 2920.00,
    "next_day_3_revenue": 2995.00,
    "confidence_score": 82,
    "growth_rate_percent": 2.5,
    "growth_direction": "Up",
    "pattern_detected": "Weekend spike pattern",
    "business_impact": "Mathematical slope shows +₹25/day growth"
  },
  "reasoning": "Based on 14-day trending pattern with 0.872 R² fit..."
}
```

#### Get Daily Weather-Optimized Tip
```http
GET /analytics/daily-tip

Authorization: Bearer {token}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "weather": {
    "condition": "Light Rain",
    "temperature": 22,
    "humidity": 78
  },
  "daily_tip": "Rain expected today (22°C, 78% humidity). Customers will order delivery. Stock up on Hot beverages & Comfort food.",
  "promotion": "Feature Paneer Chilly with complimentary hot chai - perfect for rainy weather",
  "staffing_adjustment": "Increase delivery staff by 20%, reduce floor staff by 10%"
}
```

---

### 5. Recommendations & Feedback Loop (Day 14)

#### List All Recommendations
```http
GET /recommendations

Authorization: Bearer {token}

Query Parameters:
?status=pending&limit=20
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "description": "Test +8% price on Paneer Chilly",
      "status": "pending",
      "suggested_by": "ai_consultant",
      "created_at": "2026-04-12T15:30:00Z",
      "impact_rating": null
    }
  ],
  "total": 5,
  "accepted": 3,
  "implemented": 2
}
```

#### Update Recommendation Status
```http
PATCH /recommendations/{id}

Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "accepted"
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "description": "Test +8% price on Paneer Chilly",
    "status": "accepted",
    "accepted_at": "2026-04-13T10:00:00Z"
  }
}
```

#### Verify Recommendation Impact
```http
GET /recommendations/{id}/verify-impact

Authorization: Bearer {token}

Query Parameters:
?implementation_date=2026-04-10
```

**Response (200 OK)**
```json
{
  "status": "success",
  "recommendation_id": 1,
  "description": "Test +8% price on Paneer Chilly",
  "implementation_date": "2026-04-10",
  "pre_implementation_stat": {
    "daily_sales": 120,
    "daily_revenue": 33600.00
  },
  "post_implementation_stat": {
    "daily_sales": 115,
    "daily_revenue": 36272.00,
    "revenue_change": "+₹2,672 (+7.9%)"
  },
  "impact_rating": 4.8,
  "ai_success_report": "High success! Revenue increased despite 4% drop in qty...",
  "annual_projection": "+₹975,280 if sustained year-round"
}
```

---

## Error Handling

### HTTP Status Codes
| Status | Meaning | Example |
|--------|---------|---------|
| 200 | OK | Successfully retrieved resource |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input validation error |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | User lacks required role/permission |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Duplicate email or unique constraint violation |
| 500 | Server Error | Unhandled server exception |

### Error Response Format
```json
{
  "status": "error",
  "detail": "User not found",
  "error_code": "USER_NOT_FOUND",
  "timestamp": "2026-04-13T10:30:00Z"
}
```

### Common Errors

#### 401 Unauthorized
```json
{
  "status": "error",
  "detail": "Missing or invalid Authorization header",
  "error_code": "MISSING_TOKEN"
}
```

#### 403 Forbidden (RBAC)
```json
{
  "status": "error",
  "detail": "Insufficient permissions. Required role(s): owner, manager. User role: staff",
  "error_code": "INSUFFICIENT_PERMISSIONS"
}
```

#### 400 Bad Request
```json
{
  "status": "error",
  "detail": "Invalid date format. Use YYYY-MM-DD",
  "error_code": "INVALID_DATE_FORMAT"
}
```

---

## Request/Response Examples

### Complete Workflow: Owner Checking AI Strategy

**1. Login**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=owner@restaurant.com&password=secure_password"

# Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**2. Get AI Briefing**
```bash
TOKEN="eyJhbGc..."
curl -X GET http://localhost:8000/api/v1/analytics/ai-briefing \
  -H "Authorization: Bearer $TOKEN"

# Response: Full AI strategy with recommendations
```

**3. Accept Implementation**
```bash
curl -X PATCH http://localhost:8000/api/v1/recommendations/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "accepted"}'

# Response: Recommendation marked as accepted
```

**4. Verify Impact (1 week later)**
```bash
curl -X GET http://localhost:8000/api/v1/recommendations/1/verify-impact \
  -H "Authorization: Bearer $TOKEN" \
  -d "implementation_date=2026-04-10"

# Response: Shows ROI impact of the recommendation
```

---

## Best Practices

### Security
1. Always use HTTPS in production
2. Store JWT in httpOnly cookie (not localStorage when possible)
3. Implement CORS carefully (whitelist frontend domains)
4. Never log sensitive data (passwords, tokens)
5. Rotate secrets regularly

### Performance
1. Use pagination (limit, offset) for large datasets
2. Filter by date ranges (`start_date`, `end_date`)
3. Cache responses where applicable
4. Use async/await for concurrent requests

### Error Handling
1. Always check `status` field in response
2. Log error codes for debugging
3. Implement retry logic for 500 errors
4. Show user-friendly error messages on frontend

---

## Versioning & Production Readiness

**Current Version**: 1.0  
**Production Ready**: Yes (with HTTPS, proper auth, role enforcement)  
**Next Version**: 2.0 (planned for Q2 2026)

- WebSocket support for real-time dashboards
- Advanced reporting with PDF export
- Multi-currency support
- Third-party POS integration APIs
