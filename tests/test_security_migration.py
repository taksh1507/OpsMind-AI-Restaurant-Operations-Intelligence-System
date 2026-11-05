"""Compatibility and rejection cases for the PyJWT/Argon2 migration."""

from datetime import timedelta

from argon2 import PasswordHasher
import bcrypt
import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, decode_access_token,
    hash_password, verify_password,
)


def test_new_passwords_use_argon2_and_keep_full_length():
    password = "long-password-" * 10
    hashed = hash_password(password)
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed)
    assert not verify_password(password + "wrong", hashed)


def test_existing_argon2_hash_parameters_remain_readable():
    legacy = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8)
    hashed = legacy.hash("existing password")
    assert verify_password("existing password", hashed)
    assert not verify_password("wrong password", hashed)


def test_legacy_bcrypt_and_its_truncation_remain_readable():
    password = "legacy-password-" * 8
    hashed = bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


@pytest.mark.parametrize("hashed", ["", "not-a-hash", "$argon2id$invalid", "$2b$invalid"])
def test_invalid_password_hashes_fail_closed(hashed):
    assert not verify_password("password", hashed)


def test_access_token_roundtrip_uses_hs256():
    token = create_access_token({"sub": "owner@test.com", "tenant_id": 7})
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    assert decode_access_token(token)["tenant_id"] == 7


def test_expired_and_wrong_key_tokens_are_rejected():
    expired = create_access_token({"sub": "owner@test.com"}, timedelta(seconds=-1))
    wrong_key = jwt.encode({"sub": "owner@test.com"}, "wrong-key-with-at-least-32-characters", algorithm="HS256")
    wrong_algorithm = jwt.encode({"sub": "owner@test.com"}, settings.secret_key, algorithm="HS384")
    for token in (expired, wrong_key, wrong_algorithm, "invalid-token"):
        assert decode_access_token(token) is None


def test_refresh_tokens_remain_distinct_and_cannot_be_used_as_access_tokens():
    first = create_refresh_token({"sub": "owner@test.com"})
    second = create_refresh_token({"sub": "owner@test.com"})
    assert first != second
    assert decode_access_token(first) is None
    payload = jwt.decode(first, settings.secret_key, algorithms=["HS256"])
    assert payload["type"] == "refresh"
    assert payload["jti"]
