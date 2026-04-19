# GitHub Secrets Configuration for OpsMind AI

## 🔐 Production-Ready Secret Management

This guide walks through setting up secure secrets for CI/CD deployment. Never commit sensitive data to git.

## Required Secrets for GitHub Actions

Add these to: **GitHub Repository → Settings → Secrets and variables → Actions**

### Step 1: Generate Strong JWT Secret

```bash
# Run this command to generate a secure secret
openssl rand -hex 32

# Example output (DO NOT USE - generate your own):
# a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f

# Save this value as SECRET_KEY in GitHub Secrets
```

### Step 2: Add Required Secrets

| Secret | Description | Example |
|--------|-------------|---------|
| **SECRET_KEY** | JWT signing key (from step 1) | `a1b2c3d4...` |
| **DATABASE_URL** | Production PostgreSQL connection | `postgresql+asyncpg://user:pass@host:5432/opsmind_prod` |
| **GEMINI_API_KEY** | Google Gemini API key | `AIzaSyD...` |

### Step 3: Add Optional Secrets

| Secret | Description |
|--------|-------------|
| **OPENWEATHER_API_KEY** | OpenWeatherMap API for weather features |
| **DOCKER_REGISTRY_USERNAME** | Docker Hub username for pushing images |
| **DOCKER_REGISTRY_PASSWORD** | Docker Hub token for pushing images |

## 🛡️ Security Best Practices

### ✅ DO:
- Use unique secrets for dev/staging/production
- Rotate secrets every 90 days  
- Use GitHub Secrets UI (never paste in CLI history)
- Set repo-level secrets (not user-level)
- Audit secret access logs

### ❌ DON'T:
- Commit secrets to git (even accidentally)
- Share secrets in Slack/Email
- Use same secret across environments
- Store secrets in .env files committed to git
- Use weak/default passwords

## 📋 Secrets Checklist

Before deploying to production:

- [ ] `SECRET_KEY` - Strong, random, 32+ characters
- [ ] `DATABASE_URL` - Points to production database with strong password
- [ ] `GEMINI_API_KEY` - Valid API key from Google
- [ ] `OPENWEATHER_API_KEY` - (Optional) Weather service key
- [ ] `.env` file is in `.gitignore` (never committed)
- [ ] No hardcoded secrets in code
- [ ] All secrets set in GitHub UI (not in workflow files)

## 🔄 Updating Secrets

1. Go to **Settings → Secrets and variables → Actions**
2. Click the secret name
3. Click "Update secret"
4. Paste new value
5. Save - takes effect on next workflow run

## 🚨 If Secret Is Compromised

1. Immediately update the secret in GitHub
2. Regenerate API keys (Gemini, Weather, etc.)
3. Rotate database passwords
4. Check git history: `git log --all --source -- '*secret*'` (should be empty)
5. Run security audit on production systems

## 📚 Related Documentation

- [DAY28_CICD_PIPELINE.md](DAY28_CICD_PIPELINE.md) - Full CI/CD setup
- [SECURITY.md](SECURITY.md) - Security architecture & best practices
- [SETUP.md](SETUP.md) - Local development environment

---

**Last Updated:** April 19, 2026  
**Status:** Production-Ready ✅
