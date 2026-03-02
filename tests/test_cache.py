import pytest

from hub.cache import RedisCache


@pytest.mark.asyncio
async def test_set_and_get(fake_cache: RedisCache) -> None:
    await fake_cache.set("test:key", {"foo": "bar"}, ttl=60)
    result = await fake_cache.get("test:key")
    assert result == {"foo": "bar"}


@pytest.mark.asyncio
async def test_get_missing_key(fake_cache: RedisCache) -> None:
    result = await fake_cache.get("nonexistent:key")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate(fake_cache: RedisCache) -> None:
    await fake_cache.set("test:del", "value", ttl=60)
    await fake_cache.invalidate("test:del")
    assert await fake_cache.get("test:del") is None


@pytest.mark.asyncio
async def test_invalidate_prefix(fake_cache: RedisCache) -> None:
    await fake_cache.set("weather:local", {"temp": 10}, ttl=60)
    await fake_cache.set("weather:london", {"temp": 5}, ttl=60)
    await fake_cache.set("calendar:today", {"events": []}, ttl=60)

    await fake_cache.invalidate_prefix("weather")

    assert await fake_cache.get("weather:local") is None
    assert await fake_cache.get("weather:london") is None
    # Calendar key should be unaffected
    assert await fake_cache.get("calendar:today") == {"events": []}


@pytest.mark.asyncio
async def test_health_check_ok(fake_cache: RedisCache) -> None:
    assert await fake_cache.health_check() is True


@pytest.mark.asyncio
async def test_set_serializes_datetime(fake_cache: RedisCache) -> None:
    from datetime import datetime, timezone

    now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    await fake_cache.set("test:dt", {"ts": now}, ttl=60)
    result = await fake_cache.get("test:dt")
    assert result is not None
    assert "2026-03-01" in result["ts"]
