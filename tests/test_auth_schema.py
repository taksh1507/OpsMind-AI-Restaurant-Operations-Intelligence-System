from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import text
import pytest

from app.core.config import Settings
from app.database import migrate_auth_schema
from app.services import auth_service


async def test_unknown_email_performs_a_real_dummy_password_check(db_session):
    original = auth_service.verify_password
    with patch.object(auth_service, "verify_password", wraps=original) as verify:
        assert (
            await auth_service.authenticate_user(
                db_session, "absent@example.com", "password123"
            )
            is None
        )
    verify.assert_called_once_with("password123", auth_service._DUMMY_PASSWORD_HASH)


async def test_user_schema_migration_preserves_existing_rows_and_is_idempotent(
    test_database_engine,
):
    engine = test_database_engine
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
            )
            await conn.execute(
                text("INSERT INTO users (id, email) VALUES (1, 'existing@example.com')")
            )
            await migrate_auth_schema(conn)
            await migrate_auth_schema(conn)
            assert (
                await conn.execute(text("SELECT email, token_version FROM users"))
            ).one() == (
                "existing@example.com",
                0,
            )
            await conn.execute(
                text("INSERT INTO users (id, email) VALUES (2, 'new@example.com')")
            )
            assert (
                await conn.execute(text("SELECT token_version FROM users WHERE id=2"))
            ).scalar_one() == 0
    finally:
        await engine.dispose()


def test_access_tokens_default_to_fifteen_minutes(monkeypatch):
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    assert Settings(_env_file=None).access_token_expire_minutes == 15


def test_invalid_proxy_configuration_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, trusted_proxies=["not-a-network"])


def test_multiple_workers_require_redis():
    with pytest.raises(ValidationError, match="REDIS_URL is required"):
        Settings(_env_file=None, web_concurrency=2, redis_url=None)
    assert (
        Settings(
            _env_file=None, web_concurrency=2, redis_url="redis://localhost"
        ).web_concurrency
        == 2
    )
