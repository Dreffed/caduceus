import time

from fastapi import APIRouter

from hub.dependencies import CacheDep, SettingsDep
from hub.models.common import ConnectorStatus, HealthResponse

router = APIRouter(prefix="/v1", tags=["health"])

# Module-level start time for uptime calculation
_start_time: float = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: SettingsDep,
    cache: CacheDep,
) -> HealthResponse:
    """Return hub and connector health status."""
    cache_status: ConnectorStatus = "ok" if await cache.health_check() else "error"

    # Derive overall status
    all_statuses = [cache_status]
    if all(s == "ok" for s in all_statuses):
        overall = "ok"
    elif any(s == "error" for s in all_statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version=settings.hub_version,
        uptime_seconds=time.monotonic() - _start_time,
        connectors={},
        cache=cache_status,
        queue="unknown",  # RabbitMQ consumer added in Phase 6
    )
