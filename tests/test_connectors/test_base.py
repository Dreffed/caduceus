import pytest

from hub.connectors.base import BaseConnector


class ConcreteConnector(BaseConnector):
    async def fetch(self, params: dict) -> dict:
        return {"ok": True}

    async def health_check(self) -> bool:
        return True


def test_fetch_and_health_check() -> None:
    import asyncio

    conn = ConcreteConnector()
    result = asyncio.get_event_loop().run_until_complete(conn.fetch({}))
    assert result == {"ok": True}
    assert asyncio.get_event_loop().run_until_complete(conn.health_check()) is True


def test_push_raises_not_implemented() -> None:
    import asyncio

    conn = ConcreteConnector()
    with pytest.raises(NotImplementedError, match="push"):
        asyncio.get_event_loop().run_until_complete(conn.push({}))
