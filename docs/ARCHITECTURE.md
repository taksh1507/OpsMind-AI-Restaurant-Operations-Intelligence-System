# OpsMind AI - System Architecture

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [Multi-Tenant Isolation](#multi-tenant-isolation)
5. [API Structure](#api-structure)
6. [Security Architecture](#security-architecture)

---

## Overview

OpsMind AI is a **Multi-Tenant SaaS Platform** that combines:
- **Backend**: FastAPI (async) with SQLAlchemy 2.0
- **Frontend**: Next.js 14 with TypeScript & Tailwind CSS
- **AI Engine**: Google Gemini 1.5 Flash for autonomous reasoning
- **Database**: PostgreSQL with async support
- **Authentication**: JWT-based with role-based access control

**Purpose**: Empower restaurant owners with data-driven intelligence and autonomous AI recommendations for operational optimization.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Next.js 14 Frontend (TypeScript + Tailwind CSS)         │   │
│  │  ├─ Dashboard (real-time analytics)                      │   │
│  │  ├─ Menu Management (CRUD operations)                    │   │
│  │  ├─ Sales Analytics (revenue, profit, forecasting)       │   │
│  │  ├─ AI Insights (autonomous recommendations)             │   │
│  │  └─ Staff Management (labor optimization)                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Authentication Layer                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  JWT Token (Access + Refresh)                            │   │
│  │  ├─ Claims: user_id, tenant_id, role, exp               │   │
│  │  ├─ Signed with HS256                                    │   │
│  │  └─ Role-Based Access Control (RBAC)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAPI Application (/api/v1)                           │   │
│  │  ├─ /auth (login, register, refresh)                     │   │
│  │  ├─ /customers (hyper-personalized intelligence)         │   │
│  │  ├─ /menu (menu items, categories, recipes)              │   │
│  │  ├─ /sales (transaction tracking)                        │   │
│  │  ├─ /analytics (AI insights, forecasting)                │   │
│  │  ├─ /recommendations (feedback loop)                      │   │
│  │  └─ /search (global full-text search)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Services (/app/services)                                │   │
│  │  ├─ AIConsultant (Gemini AI reasoning)                    │   │
│  │  ├─ AnalyticsService (data aggregation)                   │   │
│  │  ├─ WeatherService (environmental context)                │   │
│  │  └─ AuthService (authentication logic)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Core Utilities (/app/core)                              │   │
│  │  ├─ config.py (settings management)                       │   │
│  │  ├─ security.py (JWT & password hashing)                  │   │
│  │  ├─ math_utils.py (forecasting algorithms)                │   │
│  │  ├─ finance.py (profit/margin calculations)               │   │
│  │  └─ database.py (async DB connection)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Data Access Layer                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ORM Models (SQLAlchemy 2.0)                             │   │
│  │  ├─ Tenant (multi-tenant root)                           │   │
│  │  ├─ User (with roles: OWNER, MANAGER, STAFF)             │   │
│  │  ├─ Customer (with JSONB preferences)                    │   │
│  │  ├─ MenuItems & Categories                               │   │
│  │  ├─ Sales & SaleItems (transactional data)                │   │
│  │  ├─ Recipes & Ingredients                                │   │
│  │  ├─ Staff & Shifts                                       │   │
│  │  ├─ Reviews (with sentiment)                              │   │
│  │  ├─ Recommendations (with ROI tracking)                   │   │
│  │  └─ AICache (Gemini response caching)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ├─ PostgreSQL (primary database)                               │
│  ├─ Google Gemini 1.5 Flash (AI reasoning)                      │
│  ├─ OpenWeatherMap (environmental data)                         │
│  └─ SendGrid/SMTP (notifications)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Core Tables (Multi-Tenant Foundation)

#### **tenants** (Parent table)
- `id` (PK)
- `name` (Restaurant name)
- `domain` (Custom domain)
- `created_at`, `updated_at`

#### **users** (Multi-tenant users with RBAC)
- `id` (PK)
- `tenant_id` (FK → tenants)
- `email` (unique within tenant)
- `hashed_password`
- `role` (Enum: OWNER, MANAGER, STAFF) — Day 25 RBAC
- `is_active` (soft delete)
- `created_at`, `updated_at`

### Business Objects

#### **menu_items**
- `id` (PK)
- `tenant_id` (FK → tenants)
- `name`, `description`, `price`
- `category_id` (FK → categories)
- `cost_of_goods` (for margin calculation)
- `is_active`

#### **sales**
- `id` (PK)
- `tenant_id` (FK → tenants)
- `total_amount`, `tax_amount`
- `payment_method` (Enum)
- `timestamp` (when sale occurred)
- Multi-relationship: `sale_items`

#### **sale_items**
- `id` (PK)
- `sale_id`, `menu_item_id`, `quantity`
- `unit_price_at_sale` (immutable for history)

#### **customers** (Day 24 JSONB)
- `id` (PK)
- `tenant_id` (FK → tenants)
- `name`, `email`
- `total_spent_inr` (LTV calculation)
- `visit_count`
- `preferences` (JSONB: favorite_items, allergies, dietary, seating, spice_level)

#### **recommendations** (Day 14 Feedback Loop)
- `id` (PK)
- `tenant_id` (FK → tenants)
- `description` (AI suggestion text)
- `status` (pending, accepted, rejected, implemented)
- `impact_rating` (ROI of the suggestion)
- `actual_impact` (measured revenue change)

### Supporting Tables

#### **categories**, **recipes**, **ingredients**, **staff**, **shifts**, **reviews**, **ai_cache**

---

## Multi-Tenant Isolation

### Isolation Strategy

1. **Database Level**
   - All queries filtered by `tenant_id`
   - Foreign keys ensure cross-tenant data cannot be mixed
   - Indexes on `tenant_id` for fast filtering

2. **Application Level (API Gates)**
   - JWT claims include `tenant_id`
   - Every endpoint validates JWT tenant matches requested resource
   - `get_current_user()` dependency extracts tenant_id from JWT

3. **Data Access Layer**
   - All SQLAlchemy queries include `.where(Model.tenant_id == user.tenant_id)`
   - Prevents accidental data leakage
   - Example:
     ```python
     # ❌ WRONG - Could leak other tenants' data
     result = await db.execute(select(Sale))
     
     # ✅ RIGHT - Scoped to user's tenant
     result = await db.execute(
         select(Sale).where(Sale.tenant_id == user.tenant_id)
     )
     ```

### Guarantee
**Restaurant A cannot see Restaurant B's data**, even if a user somehow gets a valid JWT from a different restaurant.

---

## API Structure

### Authentication Routes
```
POST   /api/v1/auth/register       → Create new user + tenant
POST   /api/v1/auth/login          → Get JWT token
POST   /api/v1/auth/refresh        → Renew access token
```

### Customer Intelligence (Day 24)
```
GET    /api/v1/customers/{id}/briefing    → 3-bullet cheat sheet for staff
```

### Menu Management
```
GET    /api/v1/menu                       → List all menu items
POST   /api/v1/menu                       → Create menu item
GET    /api/v1/menu/{id}                  → Get menu item details
PATCH  /api/v1/menu/{id}                  → Update menu item
DELETE /api/v1/menu/{id}                  → Delete menu item
```

### Sales & Transactions
```
POST   /api/v1/sales                      → Record sale
GET    /api/v1/sales                      → Get sales history
```

### Analytics & AI Insights
```
GET    /api/v1/analytics                  → Overall metrics
GET    /api/v1/analytics/ai-briefing      → AI strategy recommendations
GET    /api/v1/analytics/revenue-forecast → 3-day revenue prediction
GET    /api/v1/analytics/daily-tip        → Weather-optimized promotion
```

### Recommendation Tracking (Day 14)
```
GET    /api/v1/recommendations            → List all recommendations
POST   /api/v1/recommendations            → Record new recommendation
PATCH  /api/v1/recommendations/{id}       → Mark as accepted/rejected
GET    /api/v1/recommendations/{id}/verify-impact → ROI measurement
```

---

## Security Architecture

### Authentication Flow
```
1. User registers: email + password
   ↓
2. Password hashed with bcrypt (10 rounds)
   ↓
3. User login: verify password
   ↓
4. JWT generated:
   Header: {alg: HS256, typ: JWT}
   Payload: {sub: email, tenant_id, role, exp, iat}
   Signature: HMAC-SHA256(secret)
   ↓
5. Frontend stores in localStorage
   ↓
6. Every request: Authorization: Bearer {token}
   ↓
7. Backend verifies token signature + exp date
   ↓
8. Extract user from database (fresh state)
   ↓
9. Check is_active flag + role permission
```

### Authorization (RBAC - Day 25)
```
OWNER:
├─ View all financial data (profit, margins, costs)
├─ Modify menu prices and items
├─ Manage users and staff
├─ Access all analytics and AI insights
└─ Accept/reject AI recommendations

MANAGER:
├─ View operational analytics
├─ Manage inventory and staff schedules
├─ View AI insights (limited financial data)
└─ No user management

STAFF:
├─ View dashboard (sales overview only)
├─ Manage current orders and tables
├─ Access menu for order taking
└─ No financial or admin access
```

### Role Protection Example
```python
# Only OWNER/MANAGER can see profit margins
@router.get(
    "/analytics/profit",
    dependencies=[Depends(role_required(UserRole.OWNER, UserRole.MANAGER))]
)
async def get_profit_analysis(user: User = Depends(get_current_user)):
    # If STAFF tries to access → 403 Forbidden
    pass
```

---

## Data Flow Examples

### Example 1: Restaurant Owner Checks AI Strategy
```
1. Owner clicks "Ask OpsMind" button
2. Frontend: GET /api/v1/analytics/ai-briefing (with JWT)
3. Backend:
   - Verify JWT token + extract tenant_id
   - Fetch sales data for this tenant (last 30 days)
   - Calculate: revenue, profit, margins, top items
   - Call Gemini AI with structured prompt
   - Parse AI response (JSON validation)
   - Return briefing with strategy recommendations
4. Frontend: Display 5-section briefing (star dish, price rec, etc.)
```

### Example 2: Waiter Gets Customer Briefing
```
1. Waiter scans customer ID code
2. Frontend: GET /api/v1/customers/1/briefing (with JWT)
3. Backend:
   - Fetch customer profile (LTV, visit count, preferences JSONB)
   - Fetch customer's order history
   - Call AI persona engine
   - Generate: persona, reasoning, suggested action
4. Frontend: Display 3-bullet cheat sheet
   - LTV: ₹5,400
   - Favorite: Paneer Chilly
   - AI: [High-Value Regular] Offer new Malai Kofta...
5. Waiter delivers personalized greeting
```

---

## Performance Considerations

### Indexing Strategy
- `(tenant_id, email)` on users table (multi-tenant lookup)
- `(tenant_id, created_at)` on sales table (time-based analytics)
- `role` on users table (RBAC filtering)

### Caching
- Gemini API responses cached with 1-hour TTL
- Weather data cached for 30 minutes
- Mathematical calculations cached

### Async Architecture
- All database queries use `AsyncSession`
- All API endpoints are async
- Parallel processing for multiple AI calls

---

## Deployment & Scaling

### Deployment Targets
- **Backend**: Docker container on Render/Railway/AWS ECS
- **Frontend**: Vercel (Next.js optimized)
- **Database**: Managed PostgreSQL (AWS RDS, Heroku Postgres, Supabase)
- **AI**: Google Gemini API (SaaS)

### Scaling Considerations
- Database: Connection pooling for concurrent requests
- Cache: Redis for distributed caching
- Queue: Celery for async AI tasks
- CDN: CloudFront for frontend static assets

---

## Testing Strategy

- **Unit Tests**: Per-service testing
- **Integration Tests**: API endpoint testing
- **Security Tests**: RBAC enforcement, SQL injection prevention
- **Load Tests**: Concurrent user simulation

---

## Next Steps (Future Architecture)

- **Day 26**: Recommendation Feedback Loop Enhancement
- **Day 27**: Team Coordination & AI Scheduling
- **Day 28**: Advanced Loyalty Program with AI
- **Day 30**: Real-time Websocket dashboards
