import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(async_client: AsyncClient) -> None:
    response = await async_client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert body["version"] == "0.0.0-test"
    assert "uptime_seconds" in body
    assert "cache" in body
    assert "connectors" in body


@pytest.mark.asyncio
async def test_health_cache_ok(async_client: AsyncClient) -> None:
    """fakeredis always responds — cache should report ok."""
    response = await async_client.get("/v1/health")
    body = response.json()
    assert body["cache"] == "ok"


@pytest.mark.asyncio
async def test_health_queue_unknown(async_client: AsyncClient) -> None:
    """RabbitMQ consumer not wired until Phase 6 — queue status is unknown."""
    response = await async_client.get("/v1/health")
    body = response.json()
    assert body["queue"] == "unknown"


@pytest.mark.asyncio
async def test_health_no_api_key_required(async_client: AsyncClient) -> None:
    """Health endpoint is always accessible — even when API key middleware is active."""
    response = await async_client.get("/v1/health")
    assert response.status_code == 200
