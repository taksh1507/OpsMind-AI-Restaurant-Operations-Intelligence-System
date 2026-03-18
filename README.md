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

## 🗺️ Roadmap (2026)

### **Q1 2026 — Foundation & Multi-Tenancy**
- [x] Core FastAPI Backend Setup
- [x] Multi-Tenant Architecture (isolated data per restaurant)
- [x] JWT-based Authentication & Authorization
- [x] Database Schema (Restaurants, MenuItems, Sales, Ingredients)
- [ ] **Current Focus:** Folder structure & project foundation

### **Q2 2026 — LangGraph Agents**
- [ ] Basic Agent Framework (ReAct Pattern)
- [ ] Revenue Optimization Agent
- [ ] Inventory Management Agent
- [ ] Staff Scheduling Agent
- [ ] Agent Memory & State Management

### **Q3 2026 — Analytics & Insights**
- [ ] Advanced Profit Analysis
- [ ] Time-Slot Performance Breakdown
- [ ] Predictive Revenue Forecasting (ARIMA/Prophet)
- [ ] Price Elasticity Analysis
- [ ] AI-Generated Insights (GPT Chains)

### **Q4 2026 — Dashboard & Front-End**
- [ ] Interactive React Dashboard
- [ ] Real-Time Sales Monitoring
- [ ] Agent Control Panel
- [ ] Insights & Recommendations Feed
- [ ] CSV/Excel Data Export

---

## 🏗️ Core Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Multi-Tenant Auth** | ✅ | Isolated data per restaurant owner |
| **Sales Tracking** | ✅ | CSV upload & real-time sales logging |
| **Menu Management** | ✅ | Dish pricing, ingredient tracking |
| **Revenue Analytics** | ✅ | Per-dish, per-time-slot analysis |
| **Profit Calculation** | ✅ | Ingredient cost → margin analysis |
| **Price Simulation** | ✅ | "What-if" analysis for price changes |
| **Revenue Forecasting** | 🚧 | Predictive models (ARIMA/Prophet) |
| **Autonomous Agents** | 🚧 | LangGraph-powered decision makers |
| **LLM Insights** | 🚧 | ChatGPT-powered recommendations |
| **React Dashboard** | 🚧 | Modern, real-time UI |

---

## 💾 Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Backend** | FastAPI | Async, type-safe, auto-docs |
| **Database** | PostgreSQL/SQLite | SQLAlchemy ORM for multi-tenancy |
| **Auth** | JWT | Access token + refresh token pattern |
| **AI/Agents** | LangGraph + LLM | ReAct, multi-tool agents |
| **Analytics** | NumPy + Pandas | Time-series forecasting |
| **Frontend** | React (TBD) | Vite + TypeScript |

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

## 🔐 Multi-Tenancy Model

Each restaurant is a **tenant** with:
- Unique email + password
- Isolated database records (via `restaurant_id` FK)
- JWT token bound to `restaurant_id`
- No cross-tenant data leakage

**Example Flow:**
```
1. Restaurant A registers: owner@restauranta.com
2. System creates Restaurant(id=1)
3. JWT payload: { restaurant_id: 1, email: "..." }
4. All queries filtered by restaurant_id=1
5. Restaurant B sees zero Restaurant A data
```

---

## 🤖 Autonomous Agents (LangGraph)

Future Q2/Q3 agents will include:

1. **Revenue Optimizer Agent**
   - Analyzes sales trends
   - Recommends price adjustments
   - Simulates impact
   - Takes action (auto-update menu?)

2. **Inventory Manager Agent**
   - Tracks ingredient usage
   - Predicts stockouts
   - Orders supplies
   - Alerts chef

3. **Scheduler Agent**
   - Predicts customer volume
   - Schedules staff proactively
   - Minimizes labor costs
   - Maximizes service quality

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

## 📚 API Endpoints (Current)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new restaurant |
| `POST` | `/auth/login` | Get JWT token |
| `GET` | `/analytics/summary` | Revenue dashboard |
| `POST` | `/sales/upload` | Bulk CSV upload |
| `GET` | `/menu` | List menu items |

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

**Last Updated:** March 18, 2026  
**Status:** 🚧 Active Development
