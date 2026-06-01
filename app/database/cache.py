"""Redis cache client with connection pooling and fallback."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_redis_client: Optional[Redis] = None
_memory_cache: dict[str, tuple[str, Optional[int]]] = {}  # key -> (value, ttl)


async def init_cache() -> None:
    """Initialize Redis connection pool."""
    global _redis_client
    
    if not HAS_REDIS:
        logger.warning("Redis not available, using in-memory cache fallback")
        return
    
    try:
        logger.info(f"Connecting to Redis at {settings.REDIS_URL}")
        
        _redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            connection_pool_kwargs={"max_connections": 50, "retry_on_timeout": True},
        )
        
        await _redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}, using in-memory fallback")
        _redis_client = None


async def close_cache() -> None:
    """Close Redis connection."""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")


async def cache_get(key: str) -> Optional[str]:
    """Get value from cache."""
    try:
        if _redis_client:
            value = await _redis_client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
            return value
        else:
            if key in _memory_cache:
                value, _ = _memory_cache[key]
                logger.debug(f"Memory cache hit: {key}")
                return value
            logger.debug(f"Cache miss: {key}")
            return None
    except Exception as e:
        logger.error(f"Cache get error for {key}: {e}")
        return None


async def cache_set(key: str, value: str, ttl: int = 3600) -> bool:
    """Set value in cache with TTL."""
    try:
        if _redis_client:
            await _redis_client.setex(key, ttl, value)
        else:
            _memory_cache[key] = (value, ttl)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"Cache set error for {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete value from cache."""
    try:
        if _redis_client:
            result = await _redis_client.delete(key)
            return result > 0
        else:
            if key in _memory_cache:
                del _memory_cache[key]
                return True
            return False
    except Exception as e:
        logger.error(f"Cache delete error for {key}: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching pattern."""
    try:
        if _redis_client:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await _redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await _redis_client.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        else:
            import fnmatch
            deleted = 0
            for key in list(_memory_cache.keys()):
                if fnmatch.fnmatch(key, pattern):
                    del _memory_cache[key]
                    deleted += 1
            return deleted
    except Exception as e:
        logger.error(f"Cache delete pattern error: {e}")
        return 0


async def cache_get_json(key: str) -> Optional[dict]:
    """Get JSON value from cache."""
    try:
        value = await cache_get(key)
        if value:
            return json.loads(value)
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {key}: {e}")
        return None


async def cache_set_json(key: str, value: dict, ttl: int = 3600) -> bool:
    """Set JSON value in cache."""
    try:
        json_value = json.dumps(value, default=str)
        return await cache_set(key, json_value, ttl)
    except Exception as e:
        logger.error(f"JSON encode error for {key}: {e}")
        return False


async def cache_increment(key: str, amount: int = 1) -> int:
    """Increment counter in cache (for rate limiting)."""
    try:
        if _redis_client:
            value = await _redis_client.incrby(key, amount)
            return value
        else:
            if key not in _memory_cache:
                _memory_cache[key] = ("0", 60)
            current = int(_memory_cache[key][0])
            _memory_cache[key] = (str(current + amount), 60)
            return current + amount
    except Exception as e:
        logger.error(f"Cache increment error for {key}: {e}")
        return 0


async def check_cache_health() -> bool:
    """Check if cache is accessible."""
    try:
        if _redis_client:
            await _redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return False


# Cache key generators
def make_cache_key(*parts: str, separator: str = ":") -> str:
    """Generate cache key from parts."""
    return separator.join(str(p) for p in parts if p)


def resume_cache_key(resume_id: str) -> str:
    return make_cache_key("resume", resume_id)


def job_cache_key(job_id: str) -> str:
    return make_cache_key("job", job_id)


def match_cache_key(job_id: str, resume_id: str) -> str:
    return make_cache_key("match", job_id, resume_id)


def matches_list_cache_key(job_id: str, offset: int, limit: int) -> str:
    return make_cache_key("matches:list", job_id, str(offset), str(limit))


def embedding_cache_key(resume_id: str) -> str:
    return make_cache_key("embedding", resume_id)


def ratelimit_cache_key(tenant_id: str, endpoint: str) -> str:
    return make_cache_key("ratelimit", tenant_id, endpoint)


def dashboard_cache_key(job_id: str, offset: int, limit: int) -> str:
    return make_cache_key("dashboard", job_id, str(offset), str(limit))
