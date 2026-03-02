import pytest
import fakeredis.aioredis
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from hub.cache import RedisCache
from hub.config import Settings
from hub.dependencies import get_cache, get_settings
from hub.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Override settings for tests — no real services needed."""
    return Settings(
        hub_api_key="",
        hub_debug=True,
        hub_version="0.0.0-test",
        redis_url="redis://localhost:6379/15",  # overridden by fake anyway
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
    )


@pytest.fixture
async def fake_cache() -> RedisCache:
    """Return a RedisCache backed by fakeredis (in-process, no real Redis)."""
    cache = RedisCache.__new__(RedisCache)
    cache._client = fakeredis.aioredis.FakeRedis(decode_responses=True)  # type: ignore[attr-defined]
    return cache


@pytest.fixture
async def async_client(test_settings: Settings, fake_cache: RedisCache) -> AsyncClient:
    """Async HTTPX client wired to the FastAPI app with overridden deps."""
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_cache] = lambda: fake_cache

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
