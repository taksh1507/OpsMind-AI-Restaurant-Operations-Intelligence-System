# Day 14: The Agentic Feedback & Learning Loop

## Overview

OpsMind AI transforms from a **recommendation engine** to a **learning system that proves its value**. The system now tracks every piece of advice it gives, allows users to accept/reject recommendations, and—most importantly—verifies whether those recommendations actually worked.

**Core Theme**: "AI isn't just smart. AI is accountable."

### What Changed

Previously, OpsMind would say things like:
- ❌ "You should raise burger prices" (and then never follow up)
- ❌ "Reduce staff on Mondays" (advice lost after conversation ends)
- ❌ "Your profit margin is too low" (no concrete action tracker)

Now OpsMind:
- ✅ **Saves every suggestion** in a database (Recommendation model)
- ✅ **Gets user feedback** on which ideas were implemented (Accept/Reject)
- ✅ **Measures actual impact** by comparing metrics before & after
- ✅ **Generates a success report** showing ROI: "Your decision to follow my advice on Burgers earned you an extra $200 this week!"

---

## Architecture

### 1. Recommendation Model (`app/models/recommendation.py`)

**Purpose**: Database table to persist every piece of advice the AI gives.

**Fields**:
```python
{
    "id": int,                          # Primary key
    "tenant_id": int,                   # Which restaurant (security-scoped)
    "category": str,                    # Price, Staffing, Waste, Inventory, Menu, Promotion, Operations
    "content": str,                     # The actual recommendation text (up to 2000 chars)
    "impact_score": float,              # Predicted $ impact (e.g., +$200)
    "status": str,                      # Pending → Accepted → Rejected (or stays Pending)
    "applied_date": datetime,           # When the owner acted on the recommendation
    "verified_impact": float,           # Actual measured $ impact (computed later)
    "verification_summary": str,        # AI-generated success report
    "created_at": datetime,             # When AI generated the recommendation
    "updated_at": datetime              # Last modification
}
```

**Status Flow**:
```
Pending → (User accepts) → Accepted → (Day 7+, AI verifies) → Verified with impact
       ↓
       (User rejects) → Rejected (end state)
```

**Example**:
```json
{
  "id": 42,
  "tenant_id": 5,
  "category": "Pricing",
  "content": "Your hamburger has a 32% profit margin. Industry average is 40%. Increase price from $12 to $13.50 to reach target margin. This would add ~$400/month if volume stays stable.",
  "impact_score": 400.00,
  "status": "Pending",
  "created_at": "2024-12-14T10:30:00Z"
}
```

---

### 2. Recommendations API (`app/api/recommendations.py`)

**Purpose**: REST endpoints for recommendation lifecycle management.

#### Endpoints

##### `POST /recommendations` — Create Recommendation
- **Who calls it**: The AI agent (internally)
- **Creates**: A new recommendation saved to database
- **Response**: Created recommendation with all fields

##### `GET /recommendations` — List All Recommendations
- **Query params**:
  - `status_filter`: Filter by Pending|Accepted|Rejected
  - `category_filter`: Filter by category type
  - `limit`: Max results (default 50, max 100)
- **Response**: List of all tenant's recommendations (scoped by tenant_id)

##### `GET /recommendations/{id}` — Get Single Recommendation
- **Response**: Full recommendation details
- **Security**: Only shows if `rec.tenant_id == current_user.tenant_id`

##### `PATCH /recommendations/{id}` — Update Status (THE CORE ENDPOINT)
- **Request**:
```json
{
  "status": "Accepted",
  "applied_date": "2024-12-15T10:00:00Z"  // Optional, defaults to now()
}
```
- **Logic**:
  1. Find recommendation by ID (security check: verify tenant_id matches)
  2. Ensure recommendation is still in "Pending" state
  3. Prevent changing from Accepted→Rejected or vice versa (immutable once decided)
  4. If accepting: record `applied_date` (when owner will act on it)
  5. Return updated recommendation
- **Response**: Updated recommendation with new status

##### `DELETE /recommendations/{id}` — Delete Recommendation
- **Only works**: If status is still "Pending"
- **Use case**: Owner dismisses a recommendation they don't want to track

**Example Flow**:
```bash
# 1. AI generates a suggestion (internal, automatic)
POST /recommendations
{
  "category": "Staffing",
  "content": "You're overstaffed on Tuesday mornings (Labor > 30% of sales). Cut 1 person 8am-11am to save $150/week.",
  "impact_score": 150.00
}
# Response: id=99, status="Pending"

# 2. Owner sees recommendation in dashboard, decides to implement it
PATCH /recommendations/99
{
  "status": "Accepted",
  "applied_date": "2024-12-16T08:00:00Z"  // When they'll start the change
}
# Response: id=99, status="Accepted", applied_date="2024-12-16T08:00:00Z"

# 3. Seven days later, system verifies if it worked
# (Separate verification flow—see verify_impact below)
```

---

### 3. Impact Verification (`app/services/ai_agent.py` → `verify_impact()`)

**Purpose**: The mind-blowing part. AI compares metrics before/after to measure real impact.

#### The `verify_impact()` Method

**Input**:
```python
{
    "recommendation": {
        "id": 99,
        "category": "Staffing",
        "content": "Cut 1 person Tuesday 8am-11am",
        "impact_score": 150.00
    },
    "before_metrics": {
        "revenue": 5000,
        "profit": 800,
        "profit_margin": 16,
        "specific_item_sales": 45,  // Item mentioned in recommendation
        "item_profit": 200
    },
    "after_metrics": {
        "revenue": 4900,            // Slightly down (fewer staff, fewer transactions)
        "profit": 950,              // But profit UP (labor saved)
        "profit_margin": 19.4,      // Better margin!
        "specific_item_sales": 42,  // Slightly fewer sales
        "item_profit": 195          // But still profitable
    }
}
```

**Processing**:
1. **Calculate changes**:
   - Profit change: 950 - 800 = +$150 ✅ (matched prediction!)
   - Revenue change: 4900 - 5000 = -$100
   - Margin improvement: 19.4 - 16 = +3.4%

2. **Assess prediction accuracy**:
   - Predicted: +$150
   - Actual: +$150
   - Accuracy: 100% ✅

3. **Call Gemini to write success report**:
   - Pass recommendation + metrics to AI
   - Ask AI to write a natural narrative of what happened
   - Example: "You followed my advice to reduce Tuesday morning staff. The result? You saved $150 in labor costs while maintaining profit through better efficiency. Annual value: ~$7,800."

4. **Project annual impact**:
   - If +$150 profit in 7 days → annual = +$7,800
   - Shows ROI of using the software

**Output**:
```json
{
  "status": "success",
  "recommendation_id": 99,
  "category": "Staffing",
  "original_prediction": 150.00,
  "actual_impact": 150.00,
  "prediction_accuracy_percent": 100.0,
  "success_level": "Met",
  "changes": {
    "revenue_change": -100.00,
    "profit_change": 150.00,
    "margin_change_percent": 3.4,
    "item_sales_change": -3,
    "item_profit_change": -5
  },
  "annual_projection": 7800.00,
  "success_report": "You followed my advice to reduce Tuesday morning staff by 1 person. The result exceeded expectations! Your profit jumped $150 while revenue held steady—proving you had efficiency slack. By maintaining service quality with fewer staff, you've found a sustainable win worth ~$7,800 annually.",
  "verified_at": "2024-12-21T10:00:00Z",
  "recommendation_message": "✅ AI Suggested: Cut 1 person Tuesday 8am-11am\n📊 Predicted Impact: $150.00\n💰 Actual Impact: $150.00\n📈 Annual Value: $7800.00\n\nYou followed my advice to reduce Tuesday morning staff by 1 person. The result exceeded expectations! Your profit jumped $150..."
}
```

---

## How It All Works Together

### Example: The Complete Loop (Days 1-7)

**Day 1 - AI Recommends**:
```
Restaurant owner logs in. AI analyzes last 30 days of data.
AI: "Your Iced Latte has 38% margin. Push it more. I predict +$400/month."
→ Recommendation #42 created, status=Pending
```

**Day 1 - Owner Responds**:
```
Owner sees the suggestion in /recommendations list.
Clicks "Accept" → PATCH /recommendations/42 with status="Accepted"
→ Applied date recorded: "Dec 14, 8am"
```

**Days 2-7 - Action**:
```
Owner implements: Puts Iced Latte on menu board, trains staff to upsell
Restaurant operates normally with the new push
Sales data accumulates showing Iced Latte performance
```

**Day 7 - AI Measures Impact**:
```
System queries database for recommendations accepted 7+ days ago
Finds recommendation #42 (Iced Latte price push)
Gets metrics from Dec 14-21:
  - Before: Iced Latte sales = 120 units, profit = $456
  - After: Iced Latte sales = 168 units, profit = $638
  - Impact: +$182 profit (vs $400 predicted)

Calls verify_impact(rec_42, before_metrics, after_metrics)
Gemini generates report:
  "You followed my advice to promote Iced Latté. Sales jumped 40% to 168 units weekly,
   adding $182 profit. The lower-than-predicted change suggests market saturation,
   but this is still a $9,464 annual win. Consider rotating to another item if sales plateau."
```

**Day 7 - Owner Sees Success**:
```
Dashboard shows:
✅ Recommendation #42 VERIFIED
💰 Actual Impact: +$182 (vs $400 predicted) — 45% accuracy
📈 Annual Value at current rate: $9,464
📝 AI Report: "You followed my advice..."

Owner thinks: "This AI literally told me how to make $9K+ this year. 
It's worth the subscription."
```

---

## Use Cases

### Case 1: Pricing Recommendation (Success)
```
AI: "Your burger margin is 28%. Raise to $14.50 (was $13). Predict +$300/month."
Owner accepts and implements.
7 days later: +$320 profit verified.
Success report: "Your price increase worked! You raised prices without losing customers. 
That's a $3,840 annual boost."
```

### Case 2: Waste Reduction (Partial Success)
```
AI: "Your vegetable waste is 8%. Industry is 3%. Better portion control saves $400/month."
Owner accepts training program.
7 days later: Waste reduced to 5%. Only +$100 profit (less impact than predicted).
Success report: "Partial win! Your waste improved, but customers noticed smaller portions. 
Continuing will add $1,200/year, but may impact reviews. Monitor sentiment."
```

### Case 3: Staffing Change (Rejected)
```
AI: "You're overstaffed on Sundays. Cut 2 people, save $200/week."
Owner clicks REJECT (too disruptive to implement).
Recommendation stays in history but doesn't get verified.
```

---

## Three Commits

**1. Commit `688fef6`: feat(models): add Recommendation schema to track AI-driven actions**
- Created `app/models/recommendation.py`
- Added `RecommendationCategory` and `RecommendationStatus` enums
- Updated `app/models/tenant.py` with relationship
- Updated `app/models/__init__.py` to export

**2. Commit `32cc6d8`: feat(api): implement recommendation status tracking for user feedback**
- Created `app/api/recommendations.py` with full CRUD endpoints
- Implemented PATCH endpoint for status updates with validation
- Added security checks (tenant_id scoping)
- Integrated with FastAPI app in `app/main.py`

**3. Commit `afe0446`: feat(ai): add impact verification logic to measure AI effectiveness**
- Added `verify_impact()` method to AIConsultant class
- Created `_get_impact_verification_prompt()` for Gemini
- Added `verify_recommendation_impact()` convenience function at module level
- Implemented full impact calculation and annual ROI projection

---

## Why This Is "Mind-Blowing"

Most AI tools in restaurants:
- 🤖 Generate recommendations
- 💭 Hope they help (no verification)
- 📉 Owner forgets about advice after conversation ends
- ❓ Owner never knows if AI was right

OpsMind AI now:
- 📝 **Saves** every suggestion (audit trail)
- 👤 **Tracks** which advice was implemented (owner accountability)
- 📊 **Measures** actual impact with real metrics (proof)
- 🎯 **Learns** which recommendations work best (future iteration)
- 💰 **Shows ROI**: "My OpsMind AI subscription saved me $9,864 this quarter"

**Key Insight**: Day 14 makes AI indispensable. Owners can't ignore advice they've tracked and verified worked. This transforms OpsMind from a "nice tool" to a "must-have profit center."

---

## Technical Metrics

| Component | Status | Details |
|-----------|--------|---------|
| Recommendation Model | ✅ Complete | 9 fields, enums, relationships |
| POST /recommendations | ✅ Complete | Create new recommendation |
| GET /recommendations | ✅ Complete | List with filtering |
| GET /recommendations/{id} | ✅ Complete | Single recommendation |
| PATCH /recommendations/{id} | ✅ Complete | Update status with validation |
| DELETE /recommendations/{id} | ✅ Complete | Delete Pending only |
| verify_impact() method | ✅ Complete | Full impact analysis |
| Gemini integration | ✅ Complete | Success report generation |
| Database relationships | ✅ Complete | Tenant → Many Recommendations |
| Security (tenant_id) | ✅ Complete | All endpoints scoped |

---

## Future Enhancements

1. **Learning Over Time**: Track which categories of recommendations work best
   - "Pricing recommendations: 87% accuracy"
   - "Staffing recommendations: 61% accuracy"
   - "Waste reduction recommendations: 94% accuracy"

2. **Predictive Confidence**: Adjust future predictions based on historical accuracy
   - Low-confidence recommendations get flagged for owner review
   - High-confidence recommendations auto-implement thresholds

3. **Recommendation Chains**: Some recommendations enable others
   - "Now that you've proven staffing optimization works, here's the next step..."
   - Shows progression of business improvement

4. **ROI Leaderboard**: Show owner vs. industry benchmarks
   - "Your recommendations: $45,000 annual value"
   - "Industry average: $18,000 annual value"
   - "You're in the top 15% of OpsMind users"

5. **Rejection Analysis**: Learn why owners reject recommendations
   - "83% of staffing cuts are rejected due to service concerns"
   - Adjust future prompts to address owner psychology

6. **A/B Testing Support**: For price/menu changes
   - "Try new price on Tuesday-Thursday to validate"
   - Compare results across days

---

## Summary

Day 14 completes the AI feedback loop. OpsMind AI is no longer a chatbot—it's a **decision partner** that:
1. **Makes recommendations** (Day 7-13)
2. **Accepts feedback** (Day 14 - Accept/Reject)
3. **Measures results** (Day 14 - verify_impact)
4. **Proves its value** (Day 14 - ROI reports)

This transforms the relationship from "AI gives advice" to "AI proves it helps." By the end of Day 14, restaurant owners have concrete evidence that following OpsMind AI's advice generates measurable profit increases.

**The ultimate goal**: Make OpsMind AI so indispensable that restaurants integrate it into their daily decision-making, turning it from a "neat tool" into a "core business system."
