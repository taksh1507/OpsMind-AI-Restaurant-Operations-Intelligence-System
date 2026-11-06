import pytest
from sqlalchemy.pool import StaticPool

from app import database
from app.core.config import settings


@pytest.mark.asyncio
async def test_sqlite_uses_static_pool_and_postgres_uses_bounded_queue_pool(monkeypatch):
    captured = []

    class EngineStub:
        async def dispose(self):
            return None

    def create_engine(url, **kwargs):
        captured.append((url, kwargs))
        return EngineStub()

    monkeypatch.setattr(database, "create_async_engine", create_engine)
    await database.init_db("sqlite+aiosqlite:///:memory:")
    assert captured[-1][1]["poolclass"] is StaticPool

    await database.init_db("postgresql+asyncpg://user:pass@localhost/test")
    postgres_options = captured[-1][1]
    assert postgres_options["pool_size"] == settings.db_pool_size
    assert postgres_options["max_overflow"] == settings.db_max_overflow
    assert postgres_options["pool_timeout"] == settings.db_pool_timeout
    assert postgres_options["pool_pre_ping"] is True
    assert "poolclass" not in postgres_options
    await database.close_db()


def test_anthropic_client_uses_timeout_and_bounded_retries(monkeypatch):
    from app.services import ai_agent

    captured = {}

    class ClientStub:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(settings, "anthropic_auth_token", None)
    monkeypatch.setattr(ai_agent, "Anthropic", ClientStub)

    ai_agent.AIConsultant()

    assert captured["timeout"] == settings.anthropic_timeout_seconds
    assert captured["max_retries"] == settings.anthropic_max_retries
