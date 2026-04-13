# OpsMind AI - Setup & Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Configuration](#database-configuration)
4. [Environment Variables](#environment-variables)
5. [Running the Application](#running-the-application)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **OS**: Linux/macOS/Windows (WSL2 recommended for Windows)
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 14+
- **Docker** (optional): 24.0+
- **Git**: Latest version

### Required Accounts
- **Google Cloud**: For Gemini API key (AI features)
- **Weather API**: For weather-based recommendations (optional)
- **GitHub**: For version control

---

## Local Development Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/OpsMind-AI.git
cd OpsMind-AI
```

### Step 2: Create Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows (PowerShell):
venv\Scripts\Activate.ps1

# On Windows (CMD):
venv\Scripts\activate.bat
```

### Step 3: Install Backend Dependencies
```bash
cd app/
pip install --upgrade pip
pip install -r ../requirements.txt
```

### Step 4: Install Frontend Dependencies
```bash
cd frontend/
npm install
```

### Step 5: Set Up Environment Variables
Create `.env` file in project root:
```bash
# See Environment Variables section below
cp .env.example .env
# Edit .env with your configuration
```

---

## Database Configuration

### PostgreSQL Installation

#### On macOS (using Homebrew)
```bash
brew install postgresql@14
brew services start postgresql@14
```

#### On Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install postgresql-14 postgresql-contrib-14
sudo systemctl start postgresql
```

#### On Windows
- Download from: https://www.postgresql.org/download/windows/
- Run installer with default settings
- Remember the postgres password

### Create Database and User

```bash
# Connect to PostgreSQL
psql -U postgres

# Inside psql shell:
CREATE USER opsmind_user WITH PASSWORD 'secure_password_here';
CREATE DATABASE opsmind_ai OWNER opsmind_user;

# Enable JSONB/UUID extensions
\c opsmind_ai
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

\q
```

### Initialize Database Schema

```bash
# From project root
python app/main.py --init-db

# Or using migration tools (if Alembic configured):
# alembic upgrade head
```

---

## Environment Variables

Create `.env` file in project root:

```env
# === DATABASE ===
DATABASE_URL=postgresql+asyncpg://opsmind_user:secure_password_here@localhost:5432/opsmind_ai

# === SECURITY ===
SECRET_KEY=your-super-secret-key-min-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# === AI / GEMINI ===
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# === WEATHER API (Optional) ===
WEATHER_API_KEY=your_weather_api_key_here
WEATHER_FORECAST_DAYS=3

# === CORS & FRONTEND ===
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
FRONTEND_URL=http://localhost:3000

# === LOGGING ===
LOG_LEVEL=INFO
LOG_FORMAT=json

# === ENVIRONMENT ===
ENV=development
DEBUG=true

# === EXTERNAL SERVICES ===
# If integrating with POS systems or other services
POS_WEBHOOK_SECRET=optional_webhook_secret
```

### Generating Security Keys

```bash
# Generate SECRET_KEY (min 32 characters)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API keys
openssl rand -hex 32
```

---

## Running the Application

### Backend (FastAPI)

#### Development Mode
```bash
cd app/

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or with explicit settings
uvicorn main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level info
```

**Backend will be available at**: `http://localhost:8000`  
**API Docs (Swagger UI)**: `http://localhost:8000/docs`  
**Alternative Docs (ReDoc)**: `http://localhost:8000/redoc`

#### Production Mode
```bash
# Using Gunicorn with async workers
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Frontend (Next.js)

#### Development Mode
```bash
cd frontend/

# Start Next.js dev server
npm run dev

# Or with specific port
npm run dev -- --port 3000
```

**Frontend will be available at**: `http://localhost:3000`

#### Production Build
```bash
# Build for production
npm run build

# Start production server
npm start
```

### Running Both Together

#### Using Makefile (if available)
```bash
make dev  # Starts both backend and frontend
```

#### Using Terminal Multiplexer (tmux/screen)
```bash
# Terminal 1: Backend
cd app/
source ../venv/bin/activate
uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend/
npm run dev
```

---

## Production Deployment

### Option 1: Docker Deployment

#### Build Docker Images

**Backend Dockerfile (create at project root)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile**
```dockerfile
FROM node:18 AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM node:18-slim
WORKDIR /app
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/package*.json ./
EXPOSE 3000
CMD ["npm", "start"]
```

#### Build and Run
```bash
# Build images
docker build -t opsmind-backend:latest -f Dockerfile.backend .
docker build -t opsmind-frontend:latest -f Dockerfile.frontend frontend/

# Create network
docker network create opsmind-net

# Run PostgreSQL
docker run -d \
  --name opsmind-db \
  --network opsmind-net \
  -e POSTGRES_USER=opsmind_user \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=opsmind_ai \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:14

# Run Backend
docker run -d \
  --name opsmind-backend \
  --network opsmind-net \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://opsmind_user:secure_password@opsmind-db:5432/opsmind_ai \
  -e SECRET_KEY=your_secret_key \
  -e GEMINI_API_KEY=your_api_key \
  opsmind-backend:latest

# Run Frontend
docker run -d \
  --name opsmind-frontend \
  --network opsmind-net \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 \
  opsmind-frontend:latest
```

### Option 2: Cloud Deployment

#### Heroku Deployment

```bash
# Create Heroku apps
heroku create opsmind-backend --buildpack heroku/python
heroku create opsmind-frontend --buildpack heroku/nodejs

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:standard-0 --app opsmind-backend

# Set environment variables
heroku config:set SECRET_KEY=your_secret_key --app opsmind-backend
heroku config:set GEMINI_API_KEY=your_key --app opsmind-backend
heroku config:set CORS_ORIGINS=https://opsmind-frontend.herokuapp.com --app opsmind-backend

# Deploy
git push heroku main
```

#### AWS Deployment

```bash
# Using Elastic Beanstalk
eb init opsmind-backend --platform python-3.11
eb create production
eb deploy

# Using RDS for PostgreSQL
# 1. Create RDS instance via AWS Console
# 2. Update DATABASE_URL in environment
# 3. Run migrations

# Using CloudFront for frontend distribution
# 1. Deploy frontend to S3
# 2. Create CloudFront distribution
# 3. Update CORS headers appropriately
```

#### DigitalOcean Deployment

```bash
# Using App Platform
doctl apps create --spec app.yaml

# Using Droplet + Docker Compose
# 1. Create Droplet (1GB RAM minimum)
# 2. Install Docker and Docker Compose
# 3. Copy docker-compose.yml
# 4. docker-compose up -d
```

### Environment-Specific Configuration

#### Staging
```env
ENV=staging
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/opsmind_ai
CORS_ORIGINS=https://staging.opsmind.app
```

#### Production
```env
ENV=production
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/opsmind_ai
CORS_ORIGINS=https://app.opsmind.com
SECRET_KEY=very_long_secure_random_key
```

---

## Database Migrations

### Using Alembic (if configured)

```bash
# Create new migration
alembic revision --autogenerate -m "Add user role field"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Health Checks

### Backend Health
```bash
# Basic health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "version": "1.0.0", "timestamp": "..."}
```

### Database Connection
```bash
# From backend container/app
python -c "from app.database import engine; \
           import asyncio; \
           asyncio.run(engine.connect())"
```

### Frontend Health
```bash
# Check Next.js API route
curl http://localhost:3000/api/health
```

---

## Monitoring & Logging

### Backend Logs
```bash
# View real-time logs
tail -f logs/app.log

# View with filtering
tail -f logs/app.log | grep ERROR

# Search for specific pattern
grep "get_customer_persona" logs/app.log
```

### Database Logs
```bash
# PostgreSQL slow query log
tail -f /var/log/postgresql/postgres.log | grep "duration: 1000"
```

### Frontend Console
- Open browser DevTools (F12)
- Check Console tab for errors
- Check Network tab for API failures

---

## Testing

### Run Backend Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_day24_customer_intelligence.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run with verbose output
pytest -v
```

### Run Frontend Tests
```bash
# (Configure Jest/Testing Library as needed)
npm test
```

---

## Troubleshooting

### Issue: PostgreSQL Connection Refused
**Solution**:
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Start PostgreSQL service
sudo systemctl start postgresql  # Linux
brew services start postgresql@14  # macOS

# Check connection string in .env
# Format: postgresql+asyncpg://user:password@host:port/dbname
```

### Issue: "No such file or directory" for .env
**Solution**:
```bash
# Ensure .env exists in project root
ls -la | grep .env

# If missing, create it
cp .env.example .env
# Edit with your values
```

### Issue: Gemini API Rate Limit Exceeded
**Solution**:
- Check GEMINI_API_KEY in .env
- Verify quota in Google Cloud Console
- Implement cached responses (already in code)
- Reduce API call frequency

### Issue: CORS Error on Frontend
**Solution**:
```bash
# Update CORS_ORIGINS in .env
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Restart backend
# Make sure frontend makes requests to/api/v1 endpoints correctly
```

### Issue: Frontend Cannot Connect to Backend
**Solution**:
```bash
# Check API URL in frontend environment
# Ensure backend is running: curl http://localhost:8000/health
# Check browser Network tab for failed requests
# Verify CORS_ORIGINS setting
# Check firewall rules (port 8000 open)
```

### Issue: Database Schema Mismatch
**Solution**:
```bash
# Verify database initialization
python app/main.py --init-db

# Check SQLAlchemy models match schema
# Review migration history
alembic history

# Recreate database (development only!)
rm opsmind_ai_db.sqlite3
python app/main.py --init-db
```

---

## Performance Optimization

### Backend Optimization
- Use uvicorn with multiple workers (production)
- Enable database connection pooling
- Implement caching layer (Redis optional)
- Profile slow endpoints with cProfile

### Database Optimization
- Add indexes on frequently queried columns
- Analyze query plans: `EXPLAIN ANALYZE SELECT ...`
- Archive old sales data periodically
- Use JSONB indexes for preferences column

### Frontend Optimization
- Enable Next.js Image optimization
- Implement code splitting with dynamic imports
- Use React Query for efficient caching
- Monitor Core Web Vitals

---

## Security Checklist

- [ ] Environment variables set correctly (no secrets in code)
- [ ] JWT SECRET_KEY is strong (min 32 characters)
- [ ] HTTPS enabled in production
- [ ] CORS origins restricted
- [ ] SQL injection protection (using ORM)
- [ ] Password hashing enabled (bcrypt)
- [ ] Rate limiting configured
- [ ] CSRF protection enabled
- [ ] Dependency vulnerabilities scanned: `safety check`
- [ ] Database backups scheduled
- [ ] Sensitive logs redacted

---

## Support & Documentation

- **API Docs**: See [API_REFERENCE.md](./API_REFERENCE.md)
- **Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Day 24 Details**: See [DAY24_CUSTOMER_INTELLIGENCE.md](./DAY24_CUSTOMER_INTELLIGENCE.md)
- **Issues**: Open GitHub issue with setup environment details
