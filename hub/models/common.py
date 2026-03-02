from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DegradedMixin(BaseModel):
    """Mixin for responses that can indicate a degraded/stale state."""

    cached_at: datetime | None = None
    degraded: bool = False


ConnectorStatus = Literal["ok", "error", "unknown"]


class ConnectorHealth(BaseModel):
    status: ConnectorStatus = "unknown"
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    version: str
    uptime_seconds: float
    connectors: dict[str, ConnectorStatus] = Field(default_factory=dict)
    cache: ConnectorStatus = "unknown"
    queue: ConnectorStatus = "unknown"
