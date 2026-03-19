# OpsMind AI - Day 7: The Agentic Intelligence (Phase 1)

**Commit Date**: March 19, 2026  
**Commits**: 3 commits for full agentic intelligence integration  
**Status**: ✅ Complete

---

## 📋 Overview

Day 7 integrates Google Gemini 1.5 Flash as an autonomous restaurant consultant. The AI analyzes Day 6 analytics and tells restaurant owners **exactly what to do** to improve their business.

By the end of Day 7, OpsMind AI is no longer just a database—it's a **Partner** that provides expert consulting on demand.

---

## 🎯 The Three Commits

### ✅ Commit #1: AI Service Integration

**Message**: `feat(ai): integrate Gemini 1.5 Flash for autonomous reasoning`

**What was added**:
1. `app/services/ai_agent.py` - Complete AI consultant service
   - `AIConsultant` class with Gemini integration
   - `generate_strategy()` function for restaurant analysis
   - Fallback strategy when API unavailable
   - Structured JSON output validation

2. `requirements.txt` - Updated with Google Generative AI
   - `google-generativeai==0.8.7` for Gemini access

3. `app/core/config.py` - Updated settings
   - `google_api_key` configuration option
   - Environment-based API key loading

4. `app/api/analytics.py` - Extension
   - Prepared for AI endpoint integration
   - Data aggregation ready for AI consumption

**Key Implementation**:
```python
from app.services.ai_agent import generate_restaurant_strategy

# AI takes restaurant performance data
performance_data = {
    "total_revenue": 15250.75,
    "total_profit": 4575.23,
    "profit_margin_percent": 30.0,
    "top_selling_items": [...]
}

# AI returns structured recommendations
strategy = await generate_restaurant_strategy(performance_data)
```

---

### ✅ Commit #2: Strategy Prompt Engineering

**Message**: `feat(ai): implement structured reasoning for restaurant strategy`

**What was improved**:
1. **Structured System Prompt** - Teaches AI to:
   - Identify the "Star" dish (best performer)
   - Identify the "Underperformer" (low margin + high volume)
   - Suggest ONE specific price change with financial impact
   - Suggest ONE inventory cost-saving opportunity
   - Provide overall restaurant health assessment
   - Return clean, valid JSON for frontend

2. **Detailed Prompt Engineering** - 200+ line system prompt that:
   - Instructs AI to find "Hidden Problems" in data
   - Requires specific numerical recommendations
   - Enforces JSON output format
   - Validates real menu item names from dataset
   - Prioritizes by financial impact

3. **Robust Fallback Strategy** - When API unavailable:
   - Still provides sensible defaults from actual data
   - Calculates reasonable recommendations
   - Maintains consistent JSON structure

4. **Documentation Files**:
   - `.env.example` - Shows required GOOGLE_API_KEY
   - `test_commit_1_ai_service.py` - Validation test
   - Comprehensive docstrings in `ai_agent.py`

**Expected AI Output Structure**:
```json
{
  "star_dish": {
    "name": "Truffle Fries",
    "quantity_sold": 450,
    "reason": "Highest revenue generator"
  },
  "underperformer": {
    "name": "Chocolate Mousse",
    "quantity_sold": 580,
    "problem": "High volume but thin margins"
  },
  "price_recommendation": {
    "item": "Truffle Fries",
    "current_price": 6.00,
    "suggested_price": 6.48,
    "expected_weekly_impact": "+$540 if demand stable"
  },
  "inventory_saving": {
    "area": "Waste reduction audit",
    "estimated_monthly_savings": "$320-535"
  },
  "overall_health": {
    "rating": "Good",
    "current_margin_percent": 30.0,
    "margin_target": 35.0
  },
  "top_priorities": [
    {"priority": 1, "action": "...", "expected_result": "..."}
  ]
}
```

---

### ✅ Commit #3: The "Ask OpsMind" Endpoint

**Message**: `feat(api): add autonomous AI briefing endpoint for owners`

**What was created**:
1. **GET /analytics/ai-briefing** endpoint
   - Protected by `@get_current_user` JWT dependency
   - Scoped to authenticated user's restaurant (tenant_id)
   - Optional date range filtering (start_date, end_date)
   - Returns AI-powered strategic briefing

2. **Endpoint Data Flow**:
   ```
   User Request with JWT
        ↓
   Verify authentication (JWT token valid)
        ↓
   Get tenant_id from token claims
        ↓
   Fetch restaurant analytics (filtered by tenant_id):
     - Revenue, profit, margins
     - Top 5 selling items
     - Cost of goods sold
        ↓
   Pass data to AI Consultant service
        ↓
   AI analyzes and returns strategy
        ↓
   Format response with multiple fields
        ↓
   Return 200 OK with briefing JSON
   ```

3. **Security Features**:
   - JWT authentication required
   - Multi-tenant isolation enforced
   - User can only see their own restaurant data
   - No data leakage between restaurants

4. **Test/Documentation Files**:
   - `test_commit_2_ai_endpoint.py` - Comprehensive endpoint documentation
   - Curl examples for testing
   - Error response documentation

**API Response Example**:
```json
{
  "status": "success",
  "tenant_id": 1,
  "briefing": {
    "star_dish": {...},
    "underperformer": {...},
    "price_recommendation": {...},
    "inventory_saving": {...},
    "overall_health": {...},
    "top_priorities": [...]
  },
  "data_period": {
    "start_date": "2026-02-17T00:00:00+00:00",
    "end_date": "2026-03-19T23:59:59+00:00"
  },
  "message": "AI-powered strategic briefing"
}
```

---

## 🏗️ Architecture: How It All Fits Together

```
┌─────────────────────────────────────────────────────────────┐
│                     Restaurant Owner                         │
│                  (Using OpsMind AI webapp)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                   Clicks "Ask OpsMind"
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ GET /analytics/ai-briefing                            │  │
│  │ - Check JWT token (@get_current_user dependency)     │  │
│  │ - Extract tenant_id from token                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│                    tenant_id = 1                             │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Analytics Service (Day 6+)                            │  │
│  │ - calculate_revenue_and_profit(session, tenant_id=1)  │  │
│  │ - calculate_profit_margin(session, tenant_id=1)       │  │
│  │ - get_top_selling_items(session, tenant_id=1)         │  │
│  │                                                        │  │
│  │ Returns: Performance data for this restaurant ONLY     │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ AI Consultant Service (Day 7, NEW!)                   │  │
│  │ - generate_strategy(performance_data)                 │  │
│  │ - System Prompt: Find hidden problems                 │  │
│  │ - AI Reasoning: Analyze items, margins, volumes       │  │
│  │ - Structured Output: Valid JSON with strategy         │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│      Gemini returns AI-generated recommendations             │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Format Response JSON                                  │  │
│  │ {                                                     │  │
│  │   "status": "success",                               │  │
│  │   "briefing": {                                       │  │
│  │     "star_dish": {...},                              │  │
│  │     "underperformer": {...},                          │  │
│  │     "price_recommendation": {...},                    │  │
│  │     "inventory_saving": {...},                        │  │
│  │     "overall_health": {...},                          │  │
│  │     "top_priorities": [...]                           │  │
│  │   }                                                   │  │
│  │ }                                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                    HTTP 200 OK
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Restaurant Owner                          │
│                                                              │
│  "Your Truffle Fries are a star performer. Increase price   │
│   by $1.20 to boost weekly profit by $400. Also conduct     │
│   waste audit in inventory to save $300-500/month."         │
│                                                              │
│  Takes immediate action based on AI recommendation          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 How to Use Day 7 Features

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
```bash
# Copy .env.example to .env
cp .env.example .env

# Add your Google Gemini API key
# Get it from: https://aistudio.google.com/app/apikey
export GOOGLE_API_KEY="your-api-key-here"
```

### 3. Start the Server
```bash
python -m uvicorn app.main:app --reload
```

### 4. Test the Endpoint

**Step 1: Login to get JWT token**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@pizzeria.com", "password": "password"}'

# Response:
# {"access_token": "eyJhbGc...", "token_type": "bearer"}
```

**Step 2: Call AI briefing endpoint**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/analytics/ai-briefing | jq
```

**Step 3: View recommendations**
The response includes all strategic recommendations.

---

## 🎓 Key Learnings: Why This Is "Mind-blowing"

### Before Day 7:
- Restaurant owner looks at charts
- Restaurant owner guesses what to do
- Restaurant owner makes mistakes
- Restaurant owner loses money

### After Day 7:
- Restaurant owner clicks "Ask OpsMind"
- AI consultant analyzes data in 2 seconds
- AI recommends: "Raise Truffle Fries price by $1.20"
- Restaurant owner knows EXACTLY what to do
- Restaurant owner gains $400/week profit

### The AI's Reasoning:
1. **Found the Star**: Truffle Fries = 450 units @ $6 = $2,700 revenue
2. **Found the Problem**: Current 30% margin, but with slight price increase, could be 38%
3. **Calculated Impact**: +$1.20 price × 450 units = +$540/week (if demand elastic)
4. **Risk Assessment**: Low risk because customers love this item
5. **Bonus**: Also found waste in inventory = $300-500/month savings

This is **Agentic AI** in action - the AI doesn't just show data, it reasons about the data and tells you what to do.

---

## 📊 Files Modified/Created

| File | Type | Purpose |
|------|------|---------|
| `app/services/ai_agent.py` | NEW | AI consultant service with Gemini integration |
| `app/api/analytics.py` | MODIFIED | Added /ai-briefing endpoint |
| `app/core/config.py` | MODIFIED | Added GOOGLE_API_KEY config |
| `requirements.txt` | MODIFIED | Added google-generativeai |
| `.env.example` | MODIFIED | Added GOOGLE_API_KEY documentation |
| `test_commit_1_ai_service.py` | NEW | AI service validation tests |
| `test_commit_2_ai_endpoint.py` | NEW | Endpoint documentation and examples |

---

## ☑️ Testing Checklist

- [x] AI service initializes with Gemini API
- [x] `generate_strategy()` returns structured JSON
- [x] System prompt teaches AI to find hidden problems
- [x] Endpoint requires JWT authentication
- [x] Endpoint respects tenant_id isolation
- [x] Endpoint handles missing API key gracefully
- [x] Date range filtering works
- [x] Error handling for invalid dates
- [x] Fallback strategy works when AI unavailable
- [x] Response includes all required fields
- [x] All three commits pushed to git

---

## 🔮 What's Next (Day 8 Preview)

With agentic intelligence in place, Day 8 could explore:
- Multi-turn conversations ("Ask follow-up questions to consultant")
- Custom alerts based on AI recommendations
- Automatic action tracking ("Did owner implement suggestion?")
- A/B testing results ("Did the price increase work?")
- Learning from outcomes ("Better recommendations next time")

---

## 📝 Summary

**Day 7 Achievement**: OpsMind AI transformed from a data dashboard into an autonomous consulting partner that:
- ✅ Analyzes restaurant performance automatically
- ✅ Identifies hidden problems owners would miss
- ✅ Recommends specific, actionable improvements
- ✅ Provides financial impact estimates
- ✅ Is available on-demand via simple API endpoint

**The Owner's Experience**:
```
Old OpsMind: "Here are your sales numbers..."
New OpsMind: "Your Truffle Fries are a star. Raise price $1.20 → +$400/week."
```

This is the "mind-blowing" moment where AI becomes truly useful. 🚀
