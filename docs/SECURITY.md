# OpsMind AI - Security Documentation

## Table of Contents
1. [Security Overview](#security-overview)
2. [Authentication](#authentication)
3. [Authorization & RBAC](#authorization--rbac)
4. [Data Protection](#data-protection)
5. [API Security](#api-security)
6. [Multi-Tenant Isolation](#multi-tenant-isolation)
7. [Threat Model](#threat-model)
8. [Compliance](#compliance)
9. [Security Best Practices](#security-best-practices)

---

## Security Overview

OpsMind AI implements **defense-in-depth** security with multiple layers:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: NETWORK                                           │
│  - HTTPS/TLS enforcement                                    │
│  - CORS policies                                            │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: AUTHENTICATION                                    │
│  - JWT tokens (HS256)                                       │
│  - Bcrypt password hashing                                  │
│  - Token expiration                                         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: AUTHORIZATION (RBAC)                              │
│  - Role-based access control                                │
│  - Principle of Least Privilege (PoLP)                      │
│  - Permission guards on sensitive endpoints                 │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: DATA                                              │
│  - Multi-tenant isolation (application + DB level)          │
│  - Row-level security (implicit via tenant_id)              │
│  - Encrypted sensitive fields (passwords, API keys)         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 5: APPLICATION LOGIC                                 │
│  - Input validation and sanitization                        │
│  - SQL injection prevention (ORM + parameterized queries)   │
│  - Rate limiting                                            │
│  - Audit logging                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Authentication

### JWT Implementation

#### Token Structure
```
Header.Payload.Signature

Header: { "alg": "HS256", "typ": "JWT" }
Payload: {
  "sub": "owner@restaurant.com",
  "user_id": 1,
  "tenant_id": 1,
  "role": "owner",
  "iat": 1712930400,
  "exp": 1712934000
}
Signature: HMAC-SHA256(SECRET_KEY)
```

#### Token Lifecycle
```
1. User logs in (POST /auth/login)
   ↓
2. Backend validates credentials (bcrypt compare)
   ↓
3. JWT generated with 1-hour expiration
   ↓
4. Frontend stores in httpOnly cookie or state
   ↓
5. Frontend includes in Authorization header
   ↓
6. Backend validates signature and expiration
   ↓
7. Expired tokens require re-login
```

#### Implementation Details
```python
# backend/app/core/security.py

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT token with user claims.
    
    Args:
        data: Claims to include (sub, user_id, tenant_id, role)
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"iat": datetime.utcnow(), "exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify and decode JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
```

### Password Security

#### Hashing Algorithm: Bcrypt
- **Algorithm**: Bcrypt with 10 rounds (adaptive)
- **Salt**: Automatically generated and embedded
- **Verification**: Constant-time comparison prevents timing attacks

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (constant-time comparison)."""
    return pwd_context.verify(plain_password, hashed_password)
```

#### Password Requirements
- **Minimum Length**: 8 characters
- **Complexity**: [Best Practice] Recommend uppercase + numbers + symbols
- **History**: [Future] Do not allow reuse of last 5 passwords
- **Expiration**: [Future] Force change every 90 days in production

#### Password Reset Flow
```
1. User requests reset (POST /auth/forgot-password)
2. Backend generates short-lived token (15 min expiration)
3. Email sent with reset link
4. User clicks link (validates token)
5. User sets new password (hashed with bcrypt)
6. Token invalidated
```

---

## Authorization & RBAC

### Role Hierarchy

```
┌─────────────────────┐
│      OWNER          │
│  (admin level)      │
├─────────────────────┤
│ • View all data     │
│ • Add/Edit/Delete   │
│ • Manage staff      │
│ • View financials   │
│ • Change settings   │
└──────────┬──────────┘
           │
           ├─────────────────────┐
           │                     │
┌──────────▼──────────┐  ┌──────▼──────────┐
│     MANAGER         │  │      STAFF      │
│  (supervisory)      │  │  (limited view) │
├─────────────────────┤  ├─────────────────┤
│ • View sales data   │  │ • Dashboard     │
│ • View menu         │  │ • Menu view     │
│ • Check AI insights │  │ • No analytics  │
│ • View staff        │  │ • No settings   │
│ • No settings      │  │                 │
└─────────────────────┘  └─────────────────┘
```

### Role Definitions

#### OWNER
- **Purpose**: Restaurant owner/admin
- **Permissions**:
  - ✅ All endpoints unrestricted
  - ✅ View all financial data
  - ✅ Manage menu, staff, settings
  - ✅ Access AI insights
- **Can perform**: Full system access

#### MANAGER
- **Purpose**: Shift supervisor/operations manager
- **Permissions**:
  - ✅ View dashboard
  - ✅ View menu items
  - ✅ View sales history
  - ✅ View AI insights
  - ❌ Modify prices or costs
  - ❌ Access financial settings
- **Can perform**: Operational oversight

#### STAFF
- **Purpose**: Waiter/cashier/kitchen staff
- **Permissions**:
  - ✅ View dashboard
  - ✅ View menu items and descriptions
  - ❌ View sales data
  - ❌ View analytics
  - ❌ Access settings
- **Can perform**: Basic table service operations

### RBAC Implementation

#### Role-Required Dependency (Day 25)
```python
# backend/app/api/deps.py

def role_required(*allowed_roles: UserRole) -> Callable:
    """Factory function to create role-checking dependency."""
    async def check_role(
        user: User = Depends(get_current_user)
    ) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. "
                       f"Required: {','.join(allowed_roles)}. "
                       f"User role: {user.role}"
            )
        return user
    
    return check_role

# Convenience dependencies
async def get_current_owner(
    user: User = Depends(role_required(UserRole.OWNER))
) -> User:
    return user

async def get_current_manager(
    user: User = Depends(
        role_required(UserRole.OWNER, UserRole.MANAGER)
    )
) -> User:
    return user
```

#### Usage Example
```python
@router.get("/analytics/ai-briefing")
async def get_ai_strategy_briefing(
    user: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Only OWNER and MANAGER can access AI strategic insights.
    (STAFF users get 403 Forbidden)
    """
    # ... implementation
```

### Frontend RBAC Implementation (Day 25)

```typescript
// frontend/components/ui/Sidebar.tsx

enum UserRole {
  OWNER = 'owner',
  MANAGER = 'manager',
  STAFF = 'staff'
}

const navItems = [
  {
    label: 'Dashboard',
    href: '/',
    requiredRoles: [UserRole.OWNER, UserRole.MANAGER, UserRole.STAFF]
  },
  {
    label: 'Sales',
    href: '/sales',
    requiredRoles: [UserRole.OWNER, UserRole.MANAGER]
  },
  {
    label: 'Settings',
    href: '/settings',
    requiredRoles: [UserRole.OWNER]
  }
]

// Extract role from JWT and filter nav items
const decodeJWT = (token: string) => {
  const parts = token.split('.')
  if (parts.length !== 3) return null
  
  try {
    const decoded = JSON.parse(atob(parts[1]))
    return decoded
  } catch {
    return null
  }
}

// Only render accessible menu items
const visibleItems = navItems.filter(item => 
  item.requiredRoles.includes(userRole)
)
```

---

## Data Protection

### Password Storage
- **Algorithm**: Bcrypt (adaptive, salted)
- **Rounds**: 10 (slows brute-force to milliseconds per attempt)
- **Never**: Stored in plain text, logged, or exposed in API

### Sensitive API Keys
- **Storage**: Environment variables only (.env file, not committed)
- **Transmission**: Backend-to-backend only (frontend cannot call Gemini directly)
- **Rotation**: Implement key rotation policy (quarterly)

### Customer PII (Personally Identifiable Information)
- **Data**: Names, emails, phone numbers, addresses, preferences
- **Protection**: Stored in PostgreSQL with standard encryption at rest
- **GDPR Compliance**: See [COMPLIANCE](#compliance) section

### JSONB Preferences Storage
```python
# app/models/customer.py

preferences: Mapped[dict] = mapped_column(
    JSONB,
    default=dict,
    nullable=False,
    comment="Customer preferences (spice level, allergies, favorites)"
)

# Example content:
# {
#   "favorite_items": ["Paneer Chilly", "Butter Chicken"],
#   "spice_level": "very spicy",
#   "allergies": ["peanuts"],
#   "dietary_restrictions": ["no-beef"]
# }
```

---

## API Security

### CORS (Cross-Origin Resource Sharing)
```env
# .env
CORS_ORIGINS=http://localhost:3000,https://app.opsmind.com

# Production: Only trusted domains
# Never use wildcard (*) in production
```

### Input Validation
```python
# All endpoints validate request data

@router.post("/customers")
async def create_customer(
    customer_data: CustomerSchema,  # Pydantic validation
    user: User = Depends(get_current_user)
):
    """Pydantic automatically rejects invalid input."""
    # If email invalid or price negative, 422 returned before handler runs
```

### Rate Limiting
```python
# Consider adding: pip install slowapi

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(credentials: LoginSchema):
    """Max 5 login attempts per minute per IP."""
```

### SQL Injection Prevention
```python
# ✅ SAFE: Using ORM (SQLAlchemy)
# User input automatically parameterized
customer = await db.execute(
    select(Customer).where(Customer.email == email)
)

# ✅ SAFE: Using SQLAlchemy with bindings
stmt = select(Customer).where(Customer.name.ilike(f"%{search}%"))
result = await db.execute(stmt)

# ❌ NEVER DO THIS:
# query = f"SELECT * FROM customers WHERE email = '{email}'"
```

---

## Multi-Tenant Isolation

### Tenant-Level Isolation Strategy

#### Database Level
```python
# Every row in multi-tenant tables has tenant_id

class Customer(Base):
    __tablename__ = "customers"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        index=True,  # Critical for performance
        nullable=False
    )
    name: Mapped[str]
    # ... other fields

# Every query filters by tenant_id
@router.get("/customers")
async def list_customers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # CRITICAL: Always include tenant_id filter
    stmt = select(Customer).where(
        Customer.tenant_id == user.tenant_id  # ← Implicit Row-Level Security
    )
    return await db.execute(stmt)
```

#### Application Level
```python
# JWT contains tenant_id
def create_access_token(user: User):
    return create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "tenant_id": user.tenant_id,  # ← Every request knows tenant
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
    )

# Dependency extracts tenant_id from token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = jwt.decode(token, settings.SECRET_KEY)
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")
    
    # Fetch user from DB, verify tenant_id matches
    user = await db.get(User, user_id)
    if user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    
    return user
```

### Isolation Verification
```python
# Ensure tenant_id is always included in queries

def test_multi_tenant_isolation():
    """Verify Tenant A cannot see Tenant B data."""
    
    # Create 2 tenants
    tenant_a = create_tenant("Restaurant A")
    tenant_b = create_tenant("Restaurant B")
    
    # Create users
    user_a = create_user(email="a@rest.com", tenant_id=tenant_a.id)
    user_b = create_user(email="b@rest.com", tenant_id=tenant_b.id)
    
    # User A creates customer
    customer_a = create_customer("Raj", tenant_id=tenant_a.id)
    
    # User B queries customers - should get 0 results
    token_b = create_access_token(user_b)
    response = get_customers(token=token_b)
    
    assert len(response.data) == 0, "Tenant B leaked data from Tenant A!"
    assert customer_a not in response.data
```

---

## Threat Model

### Threats & Mitigations

#### 1. Unauthorized Data Access
**Threat**: Attacker accesses customer/financial data without authorization  
**Impact**: HIGH (PII exposure, competitive data leak)  
**Mitigations**:
- ✅ JWT authentication required for all endpoints
- ✅ RBAC prevents staff from viewing financials
- ✅ Multi-tenant isolation blocks cross-tenant access
- ✅ Row-level security via tenant_id filtering

#### 2. Password Compromise
**Threat**: Attacker derives password from database dump  
**Impact**: MEDIUM-HIGH (account takeover)  
**Mitigations**:
- ✅ Bcrypt hashing (10 rounds) makes cracking slow (~milliseconds/attempt)
- ✅ Unique salt per password
- ✅ Password reset mechanism invalidates old tokens
- ✅ [Future] Implement password history (no reuse)

#### 3. JWT Token Theft
**Threat**: Attacker obtains valid JWT and makes requests  
**Impact**: MEDIUM (can impersonate user for 1 hour)  
**Mitigations**:
- ✅ Token expiration (1 hour default)
- ✅ Secure storage (httpOnly cookie recommended)
- ✅ HTTPS only transmission
- ✅ Token rotation on sensitive operations
- ⏳ [Future] Implement token refresh mechanism

#### 4. SQL Injection
**Threat**: Attacker manipulates database queries  
**Impact**: CRITICAL (full database access)  
**Mitigations**:
- ✅ SQLAlchemy ORM parameterizes all queries
- ✅ No raw SQL string concatenation
- ✅ Pydantic validates all input types

#### 5. CSRF (Cross-Site Request Forgery)
**Threat**: Attacker tricks user into making unintended requests  
**Impact**: MEDIUM (unauthorized data modification)  
**Mitigations**:
- ✅ JWT in Authorization header (not cookies) - immune to CSRF
- ✅ SameSite cookie attribute (if using cookies)
- ✅ [Future] Implement CSRF token for form-based endpoints

#### 6. Privilege Escalation
**Threat**: Staff user modifies JWT to change role to OWNER  
**Impact**: HIGH (unauthorized access to all features)  
**Mitigations**:
- ✅ JWT signature verification catches tampering
- ✅ HMAC-SHA256 requires SECRET_KEY to forge tokens
- ✅ Backend always re-verifies user.role from database
- ✅ No trusting client-side role - always check server-side

#### 7. Rate Limiting / DoS
**Threat**: Attacker floods API with requests  
**Impact**: MEDIUM (service unavailability)  
**Mitigations**:
- ⏳ [Future] Implement slowapi rate limiting
- ✅ Async processing allows handling concurrent requests
- ✅ Database connection pooling prevents exhaustion
- ⏳ [Future] Add IP-based rate limiting

#### 8. Data Breach / Ransomware
**Threat**: Attacker gains database access and exfiltrates/encrypts data  
**Impact**: CRITICAL  
**Mitigations**:
- ⏳ [Future] Enable PostgreSQL built-in encryption
- ✅ Database backups (separate from production)
- ⏳ [Future] Implement audit logging of data access
- ⏳ [Future] Add database activity monitoring

---

## Compliance

### GDPR Compliance (EU)

#### Data Subject Rights (Articles 15-22)
- **Right to Access**: Implement GET /customers/{id}/data endpoint
- **Right to Rectification**: Allow updating customer preferences
- **Right to Erasure**: Implement DELETE endpoint with soft/hard delete
- **Right to Data Portability**: Export customer data as JSON

#### Data Processing Agreement
- Document customer data processing
- Define data retention periods (e.g., 7 years for transactions)
- Specify deletion policies

#### Example: Right to Erasure
```python
@router.delete("/customers/{id}")
async def delete_customer(
    id: int,
    user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db)
):
    """
    Fully delete customer data (GDPR Article 17).
    
    Hard delete (irreversible):
    - Customer record
    - Order history
    - Preferences
    - Reviews
    """
    customer = await db.get(Customer, id)
    
    if customer.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    
    # Cascade delete
    await db.delete_cascade(customer)
    await db.commit()
    
    return {"status": "deleted"}
```

### DPDP Compliance (India)

#### Key Requirements
- Consent-based data processing
- Purpose limitation (use data only for stated purpose)
- Data minimization (collect only necessary data)
- Retention limits (delete when no longer needed)

#### Implementation
```python
# Document consent for data collection
class CustomerConsent(Base):
    __tablename__ = "customer_consents"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    consent_type: Mapped[str]  # "order_history", "preferences", "marketing"
    consented_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    is_active: Mapped[bool] = mapped_column(default=True)
```

### SOC 2 Compliance (Service Organization)

#### Type I (System Design)
- ✅ Security infrastructure documented
- ✅ Based on COSO framework
- ✅ Commitment to customer data protection

#### Type II (Operating Effectiveness)
- ⏳ [Audit Required] 6+ months of operations
- ⏳ [Audit Required] Verify controls effectiveness
- ⏳ [Audit Required] Independent auditor validation

---

## Security Best Practices

### For Developers

1. **Never Commit Secrets**
   ```bash
   # Add to .gitignore
   .env
   .env.local
   secrets.yaml
   
   # Pre-commit hook to catch accidental commits
   git config core.hooksPath .githooks
   ```

2. **Use Environment Variables**
   ```python
   # ✅ CORRECT
   import os
   api_key = os.getenv("GEMINI_API_KEY")
   
   # ❌ WRONG
   api_key = "AIzaSyBx..."  # Hardcoded in source
   ```

3. **Validate All Input**
   ```python
   # ✅ CORRECT: Pydantic validation
   class CustomerInput(BaseModel):
       email: EmailStr
       age: int = Field(ge=18, le=120)
   
   # ❌ WRONG: No validation
   def create_customer(email: str, age: int):
       pass
   ```

4. **Log Carefully**
   ```python
   # ✅ CORRECT: Don't log sensitive data
   logger.info(f"Login attempt for user: {user_id}")
   
   # ❌ WRONG: Logs password
   logger.info(f"Login: {email}:{password}")
   ```

5. **Update Dependencies**
   ```bash
   # Check for vulnerabilities
   pip install safety
   safety check
   
   # Update dependencies regularly
   pip list --outdated
   ```

### For Operators

1. **Rotate Secrets**
   - Change SECRET_KEY quarterly
   - Rotate database passwords every 90 days
   - Rotate API keys on employee departure

2. **Monitor Access Logs**
   ```bash
   # Watch for suspicious patterns
   tail -f logs/access.log | grep "403\|401"
   
   # Monitor failed login attempts
   grep "login.*failed" logs/auth.log | wc -l
   ```

3. **Regular Backups**
   ```bash
   # Automated daily backups
   pg_dump opsmind_ai | gzip > backup_$(date +%Y%m%d).sql.gz
   
   # Test restore procedures monthly
   ```

4. **Keep Systems Updated**
   ```bash
   # Update OS packages
   sudo apt-get update && sudo apt-get upgrade
   
   # Update Python packages
   pip install --upgrade -r requirements.txt
   ```

5. **Implement Monitoring**
   - Alert on failed login attempts (>5 in 5 min)
   - Alert on 403 status code spikes
   - Alert on slow queries (>1s)
   - Monitor database connection pool exhaustion

---

## Security Incident Response

### Incident Classification
- **CRITICAL**: Customer data exposed, system compromise
- **HIGH**: Privilege escalation, bulk unauthorized access
- **MEDIUM**: Single unauthorized access, failed attack
- **LOW**: Security configuration issue, vulnerability found

### Response Procedure
1. **Detect**: Monitor alerts, user reports
2. **Assess**: Determine scope and severity
3. **Contain**: Revoke compromised tokens, disable accounts
4. **Eliminate**: Patch vulnerability, update security
5. **Recover**: Restore from clean backups
6. **Analyze**: Post-mortem, log incident
7. **Communicate**: Notify affected customers (if PII exposed)

### Example: Token Compromise
```python
# If token compromised, emergency revocation:
@router.post("/auth/revoke-all-tokens")
async def revoke_all_tokens(
    user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db)
):
    """Revoke all active tokens for a user (emergency only)."""
    
    # Add all user tokens to blacklist
    # [Future] Implement token blacklist in Redis
    
    user.last_token_rotation = datetime.utcnow()
    await db.commit()
    
    return {"status": "all_tokens_revoked"}
```

---

## Security Contacts

- **Security Team**: security@opsmind.com
- **Incident Hotline**: +1-XXX-SECURITY
- **Bug Bounty Program**: [Future] https://bugbounty.opsmind.com
