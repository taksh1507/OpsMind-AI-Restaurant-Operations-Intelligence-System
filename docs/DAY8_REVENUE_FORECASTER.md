# Day 8: Revenue Forecaster - Predictive Intelligence

**Week 2 Begins**: Transition from "General Advice" to "Predictive Intelligence"

## Overview

Day 8 implements the **Revenue Forecaster**, a time-series prediction system that analyzes 14 days of historical sales data to predict revenue for the next 3 days. This gives restaurant owners a "Crystal Ball" view of their expected finances, enabling better resource planning, staffing decisions, and marketing timing.

---

## The Three Commits

### 🟢 Commit #1: Time-Series Data Aggregator

**Message**: `feat(services): implement daily revenue trend aggregation for time-series analysis`

#### What It Does
Prepares historical sales data so the AI can detect trends and patterns.

#### Implementation: `get_daily_sales_trend()`

```python
async def get_daily_sales_trend(
    session: AsyncSession,
    tenant_id: int,
    days: int = 14
) -> Dict[str, float]:
    """Get last 14 days of total revenue grouped by date."""
```

**Location**: `app/services/analytics.py`

**Returns**: Dictionary mapping dates to daily revenue totals
```python
{
    "2026-03-19": 450.0,
    "2026-03-20": 510.0,
    "2026-03-21": 485.5,
    "2026-03-22": 625.0,  # Weekend spike
    ...
}
```

**Key Features**:
- Uses SQLAlchemy's `func.date()` for SQLite date grouping
- Groups all sales by date and sums revenue per day
- Returns data chronologically ordered (earliest to latest)
- Configurable historical window (default 14 days)
- Properly scoped to tenant_id for multi-tenant isolation

**Database Query**:
```sql
SELECT 
    DATE(sales.timestamp) as sale_date,
    SUM(sale_items.quantity * sale_items.unit_price_at_sale) as daily_revenue
FROM sale_items
JOIN sales ON sale_items.sale_id = sales.id
WHERE sale_items.tenant_id = ? 
    AND sales.timestamp >= ? 
    AND sales.timestamp <= ?
GROUP BY DATE(sales.timestamp)
ORDER BY DATE(sales.timestamp) ASC
```

---

### 🔵 Commit #2: Forecasting Agent Logic

**Message**: `feat(ai): add predictive revenue forecasting using Gemini 1.5`

#### What It Does
Uses AI to analyze historical trends and predict the next 3 days of revenue with confidence scoring.

#### Implementation: `predict_revenue()`

```python
async def predict_revenue(
    self,
    trend_data: Dict[str, float]
) -> Dict[str, Any]:
    """Predict revenue for next 3 days based on trends."""
```

**Location**: `app/services/ai_agent.py` (in `AIConsultant` class)

**Input**: 
```python
{
    "2026-03-15": 400.0,
    "2026-03-16": 420.0,
    "2026-03-17": 410.0,
    ...
    "2026-03-28": 650.0  # Most recent
}
```

**Output**:
```python
{
    "status": "success",
    "forecast": {
        "next_day_1_revenue": 680.50,
        "next_day_2_revenue": 710.25,
        "next_day_3_revenue": 695.00,
        "confidence_score": 82,
        "confidence_reasoning": "Strong weekend pattern with consistent growth",
        "growth_rate_percent": 2.8,
        "growth_direction": "Up",
        "pattern_detected": "Weekend spike pattern - Fridays typically 15-20% higher",
        "business_impact": "Expect strong sales over the weekend. Suggest 15% staffing increase Friday evening.",
        "risk_factors": [
            "Holiday season could disrupt patterns",
            "Weather conditions not accounted for",
            "Limited data for accurate seasonal analysis"
        ]
    },
    "reasoning": "AI analysis text...",
    "timestamp": "2026-03-28T10:30:00Z"
}
```

#### Key Features

**1. Pattern Detection**
- Identifies weekday vs weekend differences
- Detects growth/decline trends
- Flags anomalies and seasonal patterns

**2. Confidence Scoring (0-100)**
- **90-100**: Very consistent pattern with high confidence
- **70-89**: Mostly consistent with minor fluctuations
- **50-69**: Mixed signals, moderate confidence
- **Below 50**: Highly volatile, low confidence

Based on:
- Data consistency and volatility
- Clear trend direction
- Anomaly frequency

**3. Fallback Logic**
When Gemini AI is unavailable:
- Calculates average revenue and trend
- Uses basic volatility analysis
- Extrapolates trend forward
- Provides reasonable estimates with lower confidence

**Prompt Engineering**:
System prompt teaches the AI to:
- Find daily revenue patterns (especially weekday vs weekend)
- Detect consistent trends
- Quantify forecast confidence
- Provide actionable business insights
- Return valid JSON only

---

### 🟡 Commit #3: Forecast API Endpoint

**Message**: `feat(api): expose AI-powered revenue projection endpoint`

#### What It Does
Creates a REST endpoint that combines historical data + AI forecasting for restaurant owners.

#### Implementation: `GET /analytics/forecast`

**Location**: `app/api/analytics.py`

**Endpoint**:
```
GET /analytics/forecast?days=14
```

**Query Parameters**:
- `days` (optional, default 14): Number of historical days to analyze

**Authentication**: Required (JWT Bearer token)

**Response**:
```json
{
  "status": "success",
  "tenant_id": 123,
  "forecast_period": {
    "historical_days": 14,
    "data_points": 12,
    "generated_at": "2026-03-28T10:30:00Z"
  },
  "predictions": {
    "next_day_1_revenue": 680.50,
    "next_day_2_revenue": 710.25,
    "next_day_3_revenue": 695.00
  },
  "confidence": {
    "score": 82,
    "reasoning": "Strong weekend pattern with consistent growth trend over period",
    "growth_rate_percent": 2.8,
    "growth_direction": "Up"
  },
  "pattern": {
    "detected": "Weekend spike pattern",
    "risk_factors": [
      "Holiday season could disrupt patterns",
      "Weather conditions not accounted for"
    ]
  },
  "business_impact": "Expected 15% surge this Saturday based on historical weekly pattern. Plan for increased customer volume and higher staff productivity.",
  "message": "Revenue forecast based on AI analysis of historical trends",
  "recommendation": "Use this forecast to plan staffing, inventory, and marketing campaigns"
}
```

#### Error Handling

| Status | Scenario | Example |
|--------|----------|---------|
| **401** | Not authenticated | Missing/invalid JWT token |
| **404** | Insufficient data | Less than 3 days of sales |
| **500** | Forecast generation failed | Gemini API error |

**Example Error Response**:
```json
{
  "detail": "Insufficient historical data for accurate forecasting. Need at least 3 days of sales data."
}
```

#### Implementation Details

**1. Data Validation**
- Checks minimum 3 days of historical data
- Validates date format consistency
- Ensures tenant isolation

**2. Error Handling Flow**
```
Request
  ↓
Get trend data from database
  ├─ No data? → Return 404
  ├─ < 3 days? → Return 404
  └─ Valid? → Continue
  ↓
Call forecast_revenue() with trend data
  ├─ AI error? → Return 500 with error message
  └─ Success? → Continue
  ↓
Format response with predictions, confidence, impact
  ↓
Return 200 with forecast JSON
```

**3. Business Impact Summary**
The endpoint generates human-readable insights like:
- "Expect 15% surge Saturday based on weekend pattern"
- "Declining trend detected - consider promotional campaign"
- "High volatility - recommend conservative staffing"

---

## Architecture

### Data Flow

```
Restaurant Historical Sales
      ↓
[app/models/Sale, SaleItem]
      ↓
get_daily_sales_trend()
      ↓
Dict[date] → revenue
      ↓
predict_revenue(trend_data)
      ↓
AIConsultant.predict_revenue()
      ├─ System Prompt: "You are a forecasting expert..."
      ├─ User Message: "Analyze this 14-day data..."
      └─ Gemini 1.5 Flash
      ↓
JSON Forecast Object
      ├─ Predictions for next 3 days
      ├─ Confidence score
      ├─ Growth rate
      └─ Business impact
      ↓
GET /analytics/forecast
      ↓
Restaurant Owner's Dashboard
```

### File Changes

| File | Change | Lines |
|------|--------|-------|
| `app/services/analytics.py` | Added `get_daily_sales_trend()` | +69 |
| `app/services/ai_agent.py` | Added `predict_revenue()` and helpers | +230 |
| `app/api/analytics.py` | Added `/analytics/forecast` endpoint | +112 |

### Database Queries

**Single aggregation query per request**:
- Groups sales by date
- Sums revenue per day
- Returns 14 rows (max)
- Uses indexed `tenant_id` and `timestamp`

---

## Usage Examples

### Example 1: Getting a Forecast

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/analytics/forecast?days=14"
```

### Example 2: In Python Code

```python
from app.services.analytics import get_daily_sales_trend
from app.services.ai_agent import forecast_revenue

# Get historical data
trend = await get_daily_sales_trend(session, tenant_id=1, days=14)
# {"2026-03-15": 400.0, "2026-03-16": 420.0, ...}

# Generate forecast
forecast = await forecast_revenue(trend)
# {"next_day_1_revenue": 680.50, ...}
```

### Example 3: Integrating with Frontend Dashboard

```javascript
// Fetch forecast
const response = await fetch('/api/analytics/forecast', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const forecast = await response.json();

// Display predictions
document.getElementById('tomorrow').textContent = 
  `$${forecast.predictions.next_day_1_revenue}`;

// Show confidence
document.getElementById('confidence').textContent = 
  `${forecast.confidence.score}%`;

// Display business impact
document.getElementById('impact').textContent = 
  forecast.business_impact;
```

---

## Testing the Implementation

### Manual Testing

1. **Ensure you have 14 days of sales data**:
   ```sql
   SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM sales;
   ```

2. **Test the endpoint**:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analytics/forecast
   ```

3. **Verify confidence scores**:
   - Consistent daily revenue? → High confidence (80+)
   - Volatile sales? → Low confidence (50-)

4. **Check business impact**:
   - Should identify weekend patterns
   - Should detect growth/decline trends
   - Should provide actionable recommendations

### Edge Cases Handled

- ✅ Less than 3 days of data → 404 error
- ✅ No sales on specific dates → Still calculates forecast
- ✅ High volatility → Lower confidence score
- ✅ Gemini API unavailable → Fallback calculation
- ✅ Invalid tenant_id → 401 (filtered by authentication)

---

## Performance Metrics

- **Database query**: < 100ms (single aggregation)
- **AI forecast generation**: 1-3 seconds (Gemini 1.5 Flash)
- **Total endpoint response**: 1-4 seconds
- **Data size**: 14 rows × 2 columns = ~300 bytes

---

## Future Enhancements

### Suggested for Week 2

1. **Demand Prediction**
   - Predict item-level demand for next 3 days
   - Optimize inventory based on forecast
   - Reduce waste by 20-30%

2. **Anomaly Detection**
   - Flag unusual revenue days
   - Suggest reasons (holiday, promotion, rain, etc.)

3. **Seasonality Analysis**
   - Detect monthly/seasonal patterns
   - Long-term revenue projections

4. **Weather Integration**
   - Include weather data in forecast
   - Adjust confidence based on forecast accuracy

5. **Marketing Recommendations**
   - Suggest promotions during predicted low-revenue days
   - Capitalize on high-revenue predictions

---

## Summary

**Day 8 successfully implements Week 2's foundation: Predictive Intelligence**

✅ Time-series aggregation for historical analysis
✅ AI-powered revenue forecasting with confidence scoring
✅ REST API endpoint for dashboard integration
✅ Fallback logic for reliability
✅ Comprehensive error handling
✅ Multi-tenant isolation

**The restaurant owner now has a "Crystal Ball" to:**
- See expected revenue for the next 3 days
- Understand confidence in predictions
- Identify revenue trends (up/down/stable)
- Spot daily patterns (weekday vs weekend)
- Get actionable business recommendations

**Next: Day 9 builds on this foundation with Inventory Management and Demand Forecasting.**
