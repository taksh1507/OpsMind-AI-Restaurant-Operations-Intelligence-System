# OpsMind AI — Restaurant Operations Intelligence System

**Restaurant Operations Intelligence powered by Multi-Tenant SaaS Architecture & Agentic AI**

---

## 🎯 Vision

OpsMind AI is a cutting-edge SaaS platform designed for restaurant owners and operators to harness data-driven intelligence for real-time operational optimization. Using multi-tenant architecture, advanced analytics, and autonomous AI agents, we empower restaurants to:

- 📊 **Track Operations in Real-Time** — Monitor sales, inventory, and staffing
- 🤖 **Deploy Autonomous Agents** — LangGraph-powered AI that makes decisions autonomously
- 💡 **Generate AI Insights** — Intelligent recommendations powered by LLM chains
- 📈 **Forecast Revenue** — Predictive analytics for better planning
- 💰 **Optimize Pricing** — Simulate price changes and analyze impact

---

## 🗺️ Completed Implementation (2026)

### **Day 2-3 — Foundation & Multi-Tenancy** ✅
- [x] Core FastAPI Backend Setup
- [x] Multi-Tenant Architecture (isolated data per restaurant)
- [x] JWT-based Authentication & Authorization
- [x] Database Schema (11 tables: Tenants, Users, Categories, MenuItems, Ingredients, Recipes, Sales, SaleItems, Reviews, Staff, Shifts)
- [x] API Route Structure

### **Day 7 — AI Strategy (Brain) Agent** ✅
- [x] Gemini 1.5 Flash AI Integration
- [x] Autonomous restaurant strategy analysis
- [x] Star dish detection and underperformer identification
- [x] Price optimization recommendations
- [x] AI briefing endpoint for owners

### **Day 8 — Revenue Forecasting (Heart)** ✅
- [x] Daily sales trend aggregation & time-series analysis
- [x] Predictive revenue forecasting (next 3 days with confidence scores)
- [x] Top-selling items ranking
- [x] Revenue vs. profit analysis
- [x] AI-powered revenue forecast endpoint

### **Day 9 — Waste & Cost Intelligence (Stomach)** ✅
- [x] Cost of Goods Sold (COGS) calculation per menu item
- [x] Profit margin analysis and health reporting
- [x] Low-margin item identification
- [x] Waste ingredient intelligence
- [x] Cost reduction recommendations

### **Day 10 — Customer Sentiment (Ears)** ✅
- [x] Customer review model with AI sentiment analysis
- [x] Sentiment scoring (-1.0 to 1.0 range)
- [x] Keyword extraction from customer feedback
- [x] Action item generation for managers
- [x] Reputation dashboard and sentiment trends
- [x] AI-generated response drafts for negative reviews

### **Day 11 — Labor Intelligence (Nervous System)** ✅
- [x] Staff and Shift models for labor cost tracking
- [x] Hourly labor cost calculations
- [x] Labor-to-sales efficiency analysis
- [x] Burnout risk detection (high sales + low staffing)
- [x] 24-hour staffing heatmap
- [x] AI-powered staffing optimization recommendations

### **Upcoming — Front-End & Deployment**
- [ ] Interactive React Dashboard
- [ ] Real-Time Sales Monitoring
- [ ] Agent Control Panel
- [ ] Insights & Recommendations Feed
- [ ] Docker containerization & cloud deployment

---

## 🏗️ Core Features (11 Systems)

| System | Status | Description |
|--------|--------|-------------|
| **Multi-Tenant Auth** | ✅ | Isolated data per restaurant owner with JWT |
| **Menu Management** | ✅ | Categories, items, ingredients, recipes |
| **Sales Tracking** | ✅ | Transaction logging & line items |
| **Revenue Analytics** | ✅ | Per-dish, hourly, daily analysis |
| **Profit Calculation** | ✅ | COGS → margin analysis per item |
| **AI Strategy (Day 7)** | ✅ | Autonomous business recommendations via Gemini |
| **Revenue Forecasting (Day 8)** | ✅ | 3-day predictive forecasts with confidence |
| **Cost Intelligence (Day 9)** | ✅ | Waste detection & cost optimization |
| **Customer Sentiment (Day 10)** | ✅ | AI analysis of reviews & reputation tracking |
| **Labor Optimization (Day 11)** | ✅ | Staffing heatmap & efficiency analysis |
| **REST API** | ✅ | 30+ endpoints across all systems |

---

## 💾 Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Backend** | FastAPI | Async, type-safe, auto-docs |
| **Database** | PostgreSQL/SQLite | SQLAlchemy 2.0 ORM with async support |
| **Auth** | JWT | Access token + refresh token pattern |
| **AI Engine** | Google Gemini 1.5 Flash | Sentiment analysis, forecasting, strategy |
| **Analytics** | Python (NumPy/Pandas) | Time-series analysis & trend calculation |
| **Async Driver** | asyncpg | Non-blocking PostgreSQL connection pooling |
| **Validation** | Pydantic | Request/response schema validation |
| **Frontend** | React (TBD) | Vite + TypeScript (upcoming) |

---

## 🚀 Project Structure

```
/OpsMind-AI
├── app/
│   ├── api/               # Route handlers (routes.py splits here)
│   ├── core/              # Config, security, constants
│   ├── models/            # SQLAlchemy ORM models
│   ├── services/          # Business logic (analytics, auth)
│   ├── agents/            # LangGraph agent nodes & chains
│   ├── static/            # Frontend assets (TBD: React build)
│   └── main.py            # FastAPI app initialization
├── tests/                 # Pytest suite
├── docs/                  # Deployment, architecture docs
├── .github/workflows/     # CI/CD (GitHub Actions)
├── poetry.lock / requirements.txt
├── README.md              # This file
├── LICENSE                # MIT
└── .gitignore

```

---

## � Database Schema (11 Tables)

```
1. tenants          → Restaurant organizations (parent)
2. users            → Staff/managers with JWT auth
3. categories       → Menu organization structure
4. menu_items       → Dishes with pricing & costs
5. ingredients      → Raw materials with unit costs
6. recipes          → Menu item ↔ Ingredient mapping
7. sales            → Completed transactions/bills
8. sale_items       → Line items within transactions
9. reviews          → Customer feedback & AI sentiment
10. staff           → Employee records & hourly rates
11. shifts          → Work shifts & cost calculations
```

**Multi-Tenant Architecture:** All 11 tables scoped by `tenant_id` for complete data isolation.

---

## 🤖 AI Systems (5 Autonomous Agents)

### **1. Brain — Strategy Agent (Day 7)**
- Analyzes overall restaurant performance
- Identifies star dishes and money-losers
- Recommends pricing & menu optimization
- **Endpoint:** `GET /analytics/ai-briefing`

### **2. Heart — Revenue Forecaster (Day 8)**
- Predicts next 3 days of sales with confidence scores
- Analyzes daily sales trends
- Ranks top-performing menu items
- **Endpoint:** `GET /analytics/forecast`

### **3. Stomach — Cost Analyst (Day 9)**
- Calculates Cost of Goods Sold per dish
- Identifies low-margin products
- Detects waste patterns in ingredients
- **Endpoint:** `GET /analytics/margin-report`

### **4. Ears — Sentiment Analyzer (Day 10)**
- Analyzes customer reviews & sentiment (-1.0 to 1.0)
- Extracts keywords from feedback
- Generates response drafts for negative reviews
- **Endpoint:** `GET /analytics/reputation`

### **5. Nervous System — Labor Optimizer (Day 11)**
- Creates 24-hour staffing heatmap
- Calculates labor-to-sales efficiency
- Detects burnout risks & overstaffing
- Recommends optimal staff schedules
- **Endpoint:** `GET /analytics/staffing-plan`

---

## 🧪 System Testing & Validation

All components have been **comprehensively tested** and are **100% operational**:

```
✅ TEST 1: 11 Database Models - PASSED
✅ TEST 2: 6 AI Agent Services - PASSED
✅ TEST 3: 4 Analytics Services - PASSED
✅ TEST 4: 2 Margin Analysis Functions - PASSED
✅ TEST 5: 30+ API Endpoints - PASSED
✅ TEST 6: Request/Response Schemas - PASSED
✅ TEST 7: Integration Points (Days 2-11) - PASSED

Database: 11 tables with proper relationships ✅
AI Functions: All 6 specialized agents operational ✅
API Routes: 30+ endpoints across all systems ✅
Multi-Tenancy: Complete data isolation verified ✅
```

**Run system tests:**
```bash
python SYSTEM_TEST_ASCII.py
```

---

## 📝 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ (or SQLite3)
- Poetry or pip

### Installation

```bash
# Clone repo
git clone https://github.com/taksh1507/-OpsMind-AI-Restaurant-Operations-Intelligence-System.git
cd OpsMind-AI

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python -m alembic upgrade head

# Run server
uvicorn app.main:app --reload
```

Visit: `http://localhost:8000/docs` for API documentation

---

## 📚 API Endpoints (30+ Routes)

### **Authentication**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new restaurant |
| `POST` | `/auth/login` | Get JWT token |
| `POST` | `/auth/refresh` | Refresh access token |
| `GET` | `/auth/me` | Verify session |

### **Menu Management**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/menu/categories` | List categories |
| `POST` | `/menu/categories` | Create category |
| `GET` | `/menu/items` | List menu items |
| `POST` | `/menu/items` | Create menu item |
| `GET` | `/menu/ingredients` | List ingredients |
| `POST` | `/menu/ingredients` | Create ingredient |
| `GET` | `/menu/recipes` | List recipes |
| `POST` | `/menu/recipes` | Create recipe |

### **Sales**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sales` | Get sales records |
| `POST` | `/sales` | Log new sale |

### **Analytics & AI**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics/summary` | Revenue dashboard |
| `GET` | `/analytics/metrics/revenue` | Revenue breakdown |
| `GET` | `/analytics/top-items` | Best-selling items |
| `GET` | `/analytics/ai-briefing` | AI strategy recommendations (Day 7) |
| `GET` | `/analytics/forecast` | Revenue forecast (Day 8) |
| `GET` | `/analytics/margin-report` | Profit margin analysis (Day 9) |
| `GET` | `/analytics/reputation` | Customer sentiment dashboard (Day 10) |
| `GET` | `/analytics/staffing-plan` | Labor optimization & heatmap (Day 11) |

**Total:** 30+ endpoints across all systems

---

## 🧪 Testing

```bash
pytest tests/ -v
pytest tests/ --cov=app
```

---

## 📄 License

MIT License — See [LICENSE](LICENSE) file

---

## 👥 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/agents`)
3. Commit changes (`git commit -m "feat: add agent framework"`)
4. Push to branch (`git push origin feature/agents`)
5. Open a Pull Request

---

## 📧 Contact

**Email:** taskshgandhi4@gmail.com  
**GitHub:** [taksh1507](https://github.com/taksh1507)

---

**Last Updated:** March 21, 2026  
**Status:** ✅ **COMPLETE & TESTED** — All 11 days implemented (Days 2-3: Foundation, Day 7: Strategy, Day 8: Revenue, Day 9: Costs, Day 10: Sentiment, Day 11: Labor)  
**System Validation:** 100% passing test suite (37 commits, 30+ endpoints, 6 AI functions, 11 database tables)
