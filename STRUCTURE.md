# OpsMind AI — Project Structure Documentation

## Directory Architecture

```
/OpsMind-AI
│
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI app initialization & startup events
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
│   │   ├── restaurant.py         # Restaurant (multi-tenant root)
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
│   ├── database.py               # Database connection & session factory
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
│       └── test_agents.py
│
├── docs/                         # 📖 Documentation
│   ├── API.md                    # Full API spec
│   ├── ARCHITECTURE.md           # Multi-tenant design patterns
│   ├── AGENTS.md                 # LangGraph agent design
│   └── DEPLOYMENT.md             # Docker, K8s, cloud deployment
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # GitHub Actions: test, lint
│       └── deploy.yml            # GitHub Actions: deploy to cloud
│
├── requirements.txt              # Python dependencies
├── poetry.lock                   # (if using Poetry)
├── pyproject.toml                # (if using Poetry)
├── .gitignore                    # Git ignore rules
├── LICENSE                       # MIT License
├── README.md                     # Project overview
└── STRUCTURE.md                  # This file
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
  def get_summary(db: Session = Depends(get_db), user = Depends(get_current_restaurant)):
      return analytics_service.build_summary(db, user.restaurant_id)
  ```

### `/app/core` — Configuration & Security
- **Purpose:** Centralized configuration, JWT logic, constants
- **Key Files:**
  - `config.py` — Load env variables (DB_URL, JWT_SECRET, OPENAI_KEY, etc.)
  - `security.py` — Hash passwords, encode/decode JWT tokens
  - `dependencies.py` — FastAPI `Depends()` helpers
- **Pattern:** Imported by routes & services

### `/app/models` — Database Schemas
- **Purpose:** SQLAlchemy ORM model definitions
- **Pattern:** One model per file (Restaurant, MenuItem, DailySale, etc.)
- **Multi-Tenancy:** Every model has `restaurant_id` FK or inherits from Restaurant

### `/app/services` — Business Logic
- **Purpose:** Core algorithms, calculations, orchestration
- **Pattern:** Stateless functions that operate on DB session
- **Examples:**
  - `analytics_service.calculate_profit_per_dish()`
  - `pricing_service.simulate_price_change()`
  - `agent_orchestrator.run_revenue_optimizer_agent()`

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
[Database] PostgreSQL / SQLite
    ↓
[Response] JSON to client
```

---

## 🎯 Multi-Tenancy Pattern

Every endpoint follows this pattern:

```python
@router.get("/analytics/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: Restaurant = Depends(get_current_restaurant)  # ← JWT → restaurant_id
):
    # All queries filtered by restaurant_id
    result = analytics_service.build_summary(db, current_user.restaurant_id)
    return result
```

**Key:** `current_user.restaurant_id` is passed to every service call.

---

## 🚀 What's Next?

1. ✅ **Folder Structure** (Commit #3 — TODAY)
2. 🚧 **Core Models & Database** (Commit #4)
3. 🚧 **Authentication Service** (Commit #5)
4. 🚧 **Analytics Service** (Commit #6)
5. 🚧 **LangGraph Agent Framework** (Commit #7+)

---

**Last Updated:** March 17, 2026
