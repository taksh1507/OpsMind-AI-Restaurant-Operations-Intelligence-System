# Day 28: CI/CD Pipeline & DevOps (Production-Ready)

## 📋 Overview

This document outlines the complete **Continuous Integration / Continuous Deployment (CI/CD)** setup for OpsMind AI using GitHub Actions. This represents **professional, enterprise-grade DevOps practices** used by companies like Google, Zomato, and modern startups.

**Key Achievement:** After pushing code, a "robot" automatically:
1. Runs all tests (Python + JavaScript)
2. Checks code quality & security
3. Builds Docker image
4. Scans for vulnerabilities
5. Blocks deployment if anything fails

---

## 🎯 Why Day 28 Matters

### For Placement Interviews:
- **Shows DevOps Maturity**: Automated deployments like enterprise software companies
- **Demonstrates Security-First Thinking**: Shift-left security (catch bugs early)
- **Proves Professional Practices**: Never deploy broken code
- **Scalability Ready**: Ready for Kubernetes, Lambda, or enterprise deployment
- **Compliance & Audit Trail**: Every deployment is tracked and verified

### Real-World Use Case:
```
Developer pushes code → GitHub Actions triggers automatically
  ├─ 💻 Tests run in parallel (3-5 min)
  ├─ 🔒 Security scans for vulnerabilities
  ├─ 🐳 Docker image built & scanned
  └─ ✅ Only SAFE code reaches production
```

---

## 🔧 Setup Instructions

### Step 1: Add GitHub Secrets

Go to: **GitHub Repository → Settings → Secrets and variables → Actions → New repository secret**

**Add these secrets (minimum required):**

| Secret Name | Value | Example |
|------------|-------|---------|
| `SECRET_KEY` | `openssl rand -hex 32` | `a1b2c3d4e5f6...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `GEMINI_API_KEY` | From https://ai.google.dev/ | `AIzaSyD...` |

**Generate strong SECRET_KEY:**
```bash
openssl rand -hex 32
# Output: d4f8a9c2e1b3f5a7c9e2b4d6f8a1c3e5f7a9b2d4e6f8a1c3e5f7a9b2d4f6
```

### Step 2: Configure Environment Variables

**Local Development (.env):**
```env
DATABASE_URL=sqlite+aiosqlite:///./opsmind_demo.db
SECRET_KEY=dev-key-not-for-production
GEMINI_API_KEY=your-gemini-key
DEBUG=True
ENVIRONMENT=development
```

**GitHub Actions (auto-loaded from Secrets):**
The workflow automatically passes secrets as environment variables during CI/CD runs.

---

## 🚀 Pipeline Architecture

### Workflow File: `.github/workflows/ci.yml`

```yaml
CI/CD Pipeline
├── Backend Tests
│   ├── Python 3.11 setup
│   ├── PostgreSQL test database
│   ├── Linting (flake8)
│   ├── Format check (black)
│   └── pytest suite
│
├── Frontend Tests
│   ├── Node.js 18 setup
│   ├── ESLint type checking
│   └── Next.js build verification
│
└── Docker Build & Security
    ├── Docker image build
    ├── Trivy vulnerability scan
    └── SARIF report upload
```

### Jobs Dependency Graph

```
┌─────────────────┐      ┌─────────────────┐
│  Backend Tests  │      │ Frontend Tests  │
│   (2-3 min)     │      │   (1-2 min)     │
└────────┬────────┘      └────────┬────────┘
         │                        │
         └────────────┬───────────┘
                      │
              ┌───────▼────────┐
              │  Docker Build  │
              │  + Security    │
              │   (2-3 min)    │
              └────────────────┘
```

---

## 🧪 What Gets Tested

### Backend (Python)

| Test | Tool | Purpose |
|------|------|---------|
| **Unit Tests** | pytest | Business logic validation |
| **API Tests** | pytest | Endpoint functionality |
| **Database Tests** | pytest + PostgreSQL | ORM and queries |
| **Syntax Errors** | flake8 | Code quality |
| **Format** | black | Consistent style |
| **Security Scans** | Trivy | Vulnerability detection |

**Run locally:**
```bash
pytest tests/ -v
flake8 app
black app --check
```

### Frontend (TypeScript/React)

| Test | Tool | Purpose |
|------|------|---------|
| **Type Check** | TypeScript | Type safety |
| **Linting** | ESLint | Code quality |
| **Build Test** | Next.js | Build success |

**Run locally:**
```bash
cd frontend
npm run lint
npm run build
```

### Docker

| Test | Tool | Purpose |
|------|------|---------|
| **Build Test** | Docker | Image builds successfully |
| **Vulnerability Scan** | Trivy | Detects security issues |

**Run locally:**
```bash
docker build -t opsmind:test .
trivy image opsmind:test
```

---

## 🔐 Security Scanning with Trivy

Trivy scans Docker images for vulnerabilities in dependencies and system packages.

### What Trivy Checks:
- ✅ Known CVEs in Python packages
- ✅ Known CVEs in system libraries
- ✅ Outdated dependencies
- ✅ Insecure configurations

### Severity Levels:
- 🔴 **CRITICAL** → Pipeline fails
- 🟠 **HIGH** → Pipeline fails
- 🟡 **MEDIUM** → Warning (doesn't fail)
- 🟢 **LOW** → Info only

### View Results:
1. Go to **GitHub Repository → Security tab → Code scanning alerts**
2. Or check **Actions → Latest run → build-image job**

---

## 📊 Viewing Pipeline Status

### During Pipeline Run:
1. Go to **GitHub Repository → Actions tab**
2. Click on latest workflow run
3. Watch real-time job status

### After Pipeline Completes:
- **✅ Green checkmark** = All tests passed, code is ready
- **❌ Red X** = Some tests failed, check details

### Checking Specific Job Failures:
1. Click the failed job name
2. Expand the failed step
3. Read the error message
4. Fix locally and push again

---

## 🛠️ Troubleshooting

### Problem: "Database connection refused"
**Cause:** `DATABASE_URL` secret not set  
**Solution:** Add `DATABASE_URL` to GitHub Secrets

### Problem: "pytest: command not found"
**Cause:** Dependencies not installed  
**Solution:** Check `requirements.txt` has all packages

### Problem: "GEMINI_API_KEY not found"
**Cause:** Secret not configured  
**Solution:** Add `GEMINI_API_KEY` to GitHub Secrets

### Problem: "Trivy found CRITICAL vulnerability"
**Cause:** Outdated dependency with known CVE  
**Solution:** Update package version in `requirements.txt`:
```bash
pip install --upgrade vulnerable-package
```

### Problem: "Next.js build failed"
**Cause:** TypeScript/React errors  
**Solution:** Run locally to debug:
```bash
cd frontend
npm install
npm run build
```

---

## 🔄 Typical Workflow

### Step 1: Develop Locally
```bash
# Create feature branch
git checkout -b feature/payment-system

# Make changes and test
pytest tests/
cd frontend && npm run lint

# Commit with semantic message
git commit -m "feat(payments): add payment processing"
```

### Step 2: Push to GitHub
```bash
git push origin feature/payment-system
```

### Step 3: GitHub Actions Runs
- ✅ Tests pass
- ✅ Docker builds
- ✅ Security scan passes
- ✅ All green

### Step 4: Merge to Main
```bash
# Create Pull Request (PR)
# GitHub automatically checks CI status before merge
# Once approved, merge to main branch
git checkout main
git merge feature/payment-system
```

### Step 5: Production Deploy (Optional)
```bash
# Tag release (manual step)
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# Deploy to production
docker build -t opsmind:v1.0.0 .
docker run -d opsmind:v1.0.0
```

---

## 📈 Best Practices

### ✅ DO:
- [ ] Commit small, focused changes
- [ ] Write meaningful commit messages
- [ ] Keep tests passing locally before pushing
- [ ] Rotate secrets quarterly
- [ ] Monitor security scan results
- [ ] Use semantic versioning (v1.0.0)

### ❌ DON'T:
- [ ] Commit secrets to git
- [ ] Disable failing security checks
- [ ] Hardcode API keys in code
- [ ] Skip running tests locally
- [ ] Use weak passwords
- [ ] Ignore Trivy security warnings

---

## 🎓 Learning Outcomes

By Day 28, you understand:

1. **CI/CD Principles**: Automation eliminates manual errors
2. **GitHub Actions**: Industry-standard automation tool
3. **Security-First**: Testing & scanning happen automatically
4. **DevOps Culture**: Everyone is responsible for deployment quality
5. **Scalability**: Ready for enterprise deployment
6. **Professional Standards**: How Google/Zomato/Meta ship code

---

## 🔗 Related Documentation

- [SETUP.md](SETUP.md) — Local development setup
- [SECURITY.md](SECURITY.md) — Security architecture
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design

---

## 📞 Support

If pipeline fails:
1. Check **Actions tab** for error details
2. Read error message carefully
3. Reproduce error locally
4. Fix and push again

---

**Last Updated:** April 19, 2026  
**Status:** Production-Ready ✅
