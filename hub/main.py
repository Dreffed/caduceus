import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from hub.config import Settings, get_settings
from hub.dependencies import get_cache
from hub.routers import health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown of shared resources."""
    settings = get_settings()
    logging.basicConfig(level=settings.hub_log_level.upper())
    logger.info("caduceus hub starting up (version=%s)", settings.hub_version)

    # Verify Redis connectivity at startup (non-fatal)
    cache = get_cache(settings)
    if not await cache.health_check():
        logger.warning("Redis is not reachable at startup — cache will be unavailable")

    yield

    logger.info("caduceus hub shutting down")
    await cache.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="caduceus",
        description="Personal integration hub — calendar, tasks, email, weather, AI",
        version=settings.hub_version,
        docs_url="/docs" if settings.hub_debug else None,
        redoc_url="/redoc" if settings.hub_debug else None,
        lifespan=lifespan,
    )

    # CORS — lock down in prod via HUB_API_KEY middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
    )

    # API key middleware (optional — skipped when HUB_API_KEY is empty)
    @app.middleware("http")
    async def api_key_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        key = settings.hub_api_key
        if key and request.url.path not in ("/v1/health",):
            provided = request.headers.get("X-API-Key", "")
            if provided != key:
                return Response(
                    content='{"detail":"Invalid or missing API key"}',
                    status_code=status.HTTP_403_FORBIDDEN,
                    media_type="application/json",
                )
        return await call_next(request)

    # Routers
    app.include_router(health.router)

    return app


app = create_app()
