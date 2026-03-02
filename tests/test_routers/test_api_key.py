import pytest
from httpx import AsyncClient

from hub.cache import RedisCache
from hub.config import Settings
from hub.dependencies import get_cache, get_settings
from hub.main import create_app


@pytest.fixture
async def keyed_client(fake_cache: RedisCache) -> AsyncClient:
    """Client wired to an app that enforces API key auth."""
    settings = Settings(hub_api_key="secret-key", hub_version="0.0.0-test")
    # Pass settings directly so the middleware closure captures the keyed settings
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_cache] = lambda: fake_cache

    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_bypasses_api_key(keyed_client: AsyncClient) -> None:
    """Health endpoint must be reachable without an API key."""
    response = await keyed_client.get("/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_api_key_returns_403(keyed_client: AsyncClient) -> None:
    response = await keyed_client.get("/v1/some-protected-path")
    assert response.status_code == 403
    assert "API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_wrong_api_key_returns_403(keyed_client: AsyncClient) -> None:
    response = await keyed_client.get(
        "/v1/some-protected-path", headers={"X-API-Key": "wrong"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_correct_api_key_passes(keyed_client: AsyncClient) -> None:
    """Correct key passes middleware (404 is from router, not auth)."""
    response = await keyed_client.get(
        "/v1/some-protected-path", headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 404  # path doesn't exist, but auth passed
