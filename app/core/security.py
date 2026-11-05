"""Security Utilities for Password Hashing and JWT Token Management

Includes:
- Password hashing with Argon2 and legacy bcrypt verification
- JWT access token creation and validation
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import uuid4
import jwt
from jwt import InvalidTokenError
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from .config import settings


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
    """
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against
        
    Returns:
        True if passwords match, False otherwise
    """
    try:
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            # Match legacy passlib's 72-byte bcrypt truncation. New Argon2
            # passwords retain their full length.
            return bcrypt.checkpw(
                plain_password.encode("utf-8")[:72], hashed_password.encode("ascii")
            )
        return password_hasher.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError, ValueError, TypeError):
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary of claims to include in token (sub, user_id, tenant_id, etc.)
        expires_delta: Custom expiration time. If None, uses settings.access_token_expire_minutes
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.setdefault("token_version", 0)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Dictionary of claims if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        # Reject refresh tokens presented as access tokens. Refresh tokens carry
        # {"type": "refresh"} and must only be accepted at the refresh endpoint.
        if payload.get("type") == "refresh":
            return None
        return payload
    except InvalidTokenError:
        return None


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token (longer expiration).
    
    Args:
        data: Dictionary of claims to include in token
        expires_delta: Custom expiration time. If None, uses settings.refresh_token_expire_days
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
    
    # Unique jti (JWT ID) guarantees each refresh token is distinct, even when
    # issued within the same second, so rotating/revoking cannot collide.
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid4().hex})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify refresh JWT signature and expiry before using its version claim."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload if payload.get("type") == "refresh" else None
    except InvalidTokenError:
        return None
