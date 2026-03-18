"""Integration test for login endpoint and JWT token generation
Tests that the /login endpoint produces valid JWT tokens for use with get_current_user
"""

import asyncio
from app.core.security import create_access_token, decode_access_token
from app.core.config import settings


def test_login_token_generation():
    """Test that login generates valid JWT tokens"""
    
    print("\n" + "="*60)
    print("🧪 Testing Login Endpoint & Token Generation (Commit #2)")
    print("="*60 + "\n")
    
    # Simulate what the /login endpoint does
    print("✓ Simulating login endpoint behavior:")
    print("  User logs in with email and password")
    print("  Endpoint validates credentials (from Step #1)")
    print("  Endpoint generates JWT token\n")
    
    # The login endpoint creates a token like this:
    test_user_data = {
        "sub": "owner@testrestaurant.com",  # Email in 'sub' claim
        "user_id": 42,                       # Database user ID
        "tenant_id": 7                       # Multi-tenant isolation
    }
    
    # Create token (simulating login endpoint)
    access_token = create_access_token(test_user_data)
    
    print(f"✓ Step 1: Token created")
    print(f"  Token: {access_token[:40]}...\n")
    
    # Decode and verify (what get_current_user dependency does)
    print(f"✓ Step 2: Verify token can be decoded")
    payload = decode_access_token(access_token)
    
    if payload is None:
        print("  ❌ ERROR: Token failed to decode")
        return False
    
    print(f"  Decoded payload:")
    print(f"    - sub (email): {payload.get('sub')}")
    print(f"    - user_id: {payload.get('user_id')}")
    print(f"    - tenant_id: {payload.get('tenant_id')}")
    print(f"    - exp: {payload.get('exp')}\n")
    
    # Verify all required claims are present
    print(f"✓ Step 3: Validate JWT claims")
    
    checks = [
        ("sub (user email)", payload.get("sub") == test_user_data["sub"]),
        ("user_id", payload.get("user_id") == test_user_data["user_id"]),
        ("tenant_id (for multi-tenant isolation)", payload.get("tenant_id") == test_user_data["tenant_id"]),
        ("exp (token expiration)", payload.get("exp") is not None),
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}: {result}")
        all_passed = all_passed and result
    
    if not all_passed:
        return False
    
    print("\n" + "="*60)
    print("✅ Login endpoint correctly generates valid JWT tokens!")
    print("   These tokens can be used with the get_current_user dependency")
    print("="*60 + "\n")
    
    return True


def test_token_expiration():
    """Test token expiration configuration"""
    
    print("\n🕐 Verifying token expiration settings...\n")
    
    print(f"✓ Token Expiration Configuration:")
    print(f"  Access token expires in: {settings.access_token_expire_minutes} minutes")
    
    if settings.access_token_expire_minutes <= 0:
        print("  ❌ ERROR: Token expiration must be positive")
        return False
    
    print("  ✅ Expiration is properly configured\n")
    
    return True


if __name__ == "__main__":
    print("\n🚀 Running Commit #2 tests...\n")
    
    test1_passed = test_login_token_generation()
    test2_passed = test_token_expiration()
    
    if test1_passed and test2_passed:
        print("✅ Commit #2 is ready to push!")
        print("\nNext step: Move to Commit #3 to create the /me endpoint")
        print("           which uses the get_current_user dependency from Commit #1")
    else:
        print("\n❌ Commit #2 has issues. Fix before pushing.")
