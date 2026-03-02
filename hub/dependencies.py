from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from hub.cache import RedisCache
from hub.config import Settings, get_settings


@lru_cache
def get_cache(settings: Settings = Depends(get_settings)) -> RedisCache:
    """FastAPI dependency — returns a cached RedisCache instance."""
    return RedisCache(settings.redis_url)


# Type aliases for injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
CacheDep = Annotated[RedisCache, Depends(get_cache)]
