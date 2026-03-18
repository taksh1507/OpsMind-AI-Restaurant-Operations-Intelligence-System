# OpsMind AI — Project Structure Documentation

## Directory Architecture

```
/OpsMind-AI
│
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI app initialization & startup events
│   ├── database.py               # Database connection & session factory
│   │
│   ├── api/                      # 🔗 Route Handlers
│   │   ├── __init__.py
│   │   ├── auth.py               # POST /auth/register, /auth/login
│   │   ├── sales.py              # POST /sales/upload, GET /sales
│   │   ├── analytics.py          # GET /analytics/summary, /analytics/insights
│   │   ├── menu.py               # GET /menu, POST /menu, PUT /menu/{id}
│   │   └── agents.py             # GET /agents/status, POST /agents/run
│   │
│   ├── core/                     # ⚙️ Configuration & Security
│   │   ├── __init__.py
│   │   ├── config.py             # Environment variables, settings
│   │   ├── security.py           # JWT encoding/decoding, password hashing
│   │   ├── constants.py          # App-wide constants
│   │   └── dependencies.py       # FastAPI dependency injection
│   │
│   ├── models/                   # 🗂️ Database Schemas (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── base.py               # Base model & registry
│   │   ├── tenant.py             # Tenant (multi-tenant root)
│   │   ├── user.py               # User accounts
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── menu_item.py          # Menu items
│   │   ├── daily_sale.py         # Daily sales transactions
│   │   ├── ingredient.py         # Raw ingredients & costs
│   │   └── dish_ingredient.py    # Many-to-many: dish ↔ ingredient
│   │
│   ├── services/                 # 💼 Business Logic
│   │   ├── __init__.py
│   │   ├── auth_service.py       # Register, login, token validation
│   │   ├── analytics_service.py  # Revenue, profit, forecasting calculations
│   │   ├── sales_service.py      # CSV parsing, data loading, validation
│   │   ├── menu_service.py       # Menu CRUD & inventory mgmt
│   │   ├── pricing_service.py    # Price elasticity, "what-if" simulation
│   │   └── agent_orchestrator.py # Coordinates autonomous agents
│   │
│   ├── agents/                   # 🤖 LangGraph Autonomous Agents
│   │   ├── __init__.py
│   │   ├── base_agent.py         # Base agent class & utilities
│   │   ├── revenue_optimizer.py  # Agent: Optimize pricing & margins
│   │   ├── inventory_manager.py  # Agent: Predict stockouts, order supplies
│   │   ├── scheduler.py          # Agent: Staff scheduling
│   │   └── state.py              # Shared agent state & schemas
│   │
│   ├── static/                   # Frontend assets
│   │   ├── index.html
│   │   ├── dashboard.js
│   │   └── styles.css
│   └── __pycache__/              # (ignored by .gitignore)
│
├── tests/                        # 🧪 Test Suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures & setup
│   ├── test_api/
│   │   ├── test_auth.py
│   │   ├── test_sales.py
│   │   └── test_analytics.py
│   ├── test_services/
│   │   ├── test_auth_service.py
│   │   └── test_analytics_service.py
│   └── test_agents/
│       └── test_agents.js
│
├── docs/                         # 📖 Documentation
│   ├── STRUCTURE.md              # Project structure (this file)
│   ├── DAY2_IMPLEMENTATION.md    # Day 2 implementation details
│   ├── API.md                    # Full API specification
│   ├── ARCHITECTURE.md           # Multi-tenant design patterns
│   ├── AGENTS.md                 # LangGraph agent design
│   └── DEPLOYMENT.md             # Docker, K8s, cloud deployment
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # GitHub Actions: test, lint
│       └── deploy.yml            # GitHub Actions: deploy to cloud
│
├── .env                          # Local environment config (gitignored)
├── .env.example                  # Environment config template
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
├── LICENSE                       # MIT License
├── README.md                     # Project overview
└── STRUCTURE.md                  # ⚠️ DEPRECATED - See docs/STRUCTURE.md
```

---

## 📁 Folder Purposes

### `/app/api` — Route Handlers
- **Purpose:** Define all HTTP endpoints
- **Pattern:** Each file = logical grouping of related endpoints
- **Dependency:** Calls `/services` for business logic
- **Example:**
  ```python
  # app/api/analytics.py
  @router.get("/analytics/summary")
  async def get_summary(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
      return await analytics_service.build_summary(db, user.tenant_id)
  ```

### `/app/core` — Configuration & Security
- **Purpose:** Centralized configuration, JWT logic, constants
- **Key Files:**
  - `config.py` — Load env variables (DATABASE_URL, SECRET_KEY, etc.)
  - `security.py` — Hash passwords, encode/decode JWT tokens
  - `dependencies.py` — FastAPI `Depends()` helpers
- **Pattern:** Imported by routes & services

### `/app/models` — Database Schemas
- **Purpose:** SQLAlchemy ORM model definitions + Pydantic schemas
- **Pattern:** One model per file (Tenant, User, MenuItem, DailySale, etc.)
- **Multi-Tenancy:** Every user model has `tenant_id` FK to Tenant

### `/app/services` — Business Logic
- **Purpose:** Core algorithms, calculations, orchestration
- **Pattern:** Stateless async functions that operate on DB session
- **Examples:**
  - `auth_service.register_user()`
  - `analytics_service.calculate_profit_per_dish()`
  - `pricing_service.simulate_price_change()`

### `/app/agents` — LangGraph Agents
- **Purpose:** Autonomous AI agents powered by LangGraph
- **Pattern:** Each agent = a LangGraph StateGraph
- **Examples:**
  - `revenue_optimizer.py` — ReAct loop: Analyze → Recommend → Execute
  - `inventory_manager.py` — Predict stockouts, place orders
  - `scheduler.py` — Staff scheduling based on demand forecast

---

## 🔄 Data Flow Example

```
USER REQUEST
    ↓
[API Route] app/api/analytics.py
    ↓ calls
[Service] app/services/analytics_service.py
    ↓ queries
[Models] app/models/daily_sale.py, menu_item.py
    ↓ reads
[Database] PostgreSQL (async with asyncpg)
    ↓
[Response] JSON to client
```

---

## 🎯 Multi-Tenancy Pattern

Every endpoint follows this pattern:

```python
@router.get("/analytics/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ← JWT → tenant_id
):
    # All queries filtered by tenant_id
    result = await analytics_service.build_summary(db, current_user.tenant_id)
    return result
```

**Key:** `current_user.tenant_id` is passed to every service call for isolation.

---

## 🔐 Security Architecture

- **Authentication:** JWT tokens (HS256)
- **Password Storage:** Bcrypt hashing with passlib
- **Multi-Tenancy:** Database-level isolation per tenant
- **Authorization:** Role-based access control (RBAC) - future implementation

---

## 🚀 Development Roadmap

### Day 1 ✅ — Skeleton
- [x] FastAPI folder structure
- [x] Core models package
- [x] Git initialization

### Day 2 ✅ — Foundation of Trust
- [x] SQLAlchemy Tenant + User models
- [x] JWT security utilities
- [x] Registration & Login endpoints

### Day 3+ — Features (Planned)
- [ ] Database Migrations (Alembic)
- [ ] Role-Based Access Control
- [ ] Analytics Service
- [ ] LangGraph Agent Framework
- [ ] Tests & CI/CD

---

**Last Updated:** March 18, 2026
