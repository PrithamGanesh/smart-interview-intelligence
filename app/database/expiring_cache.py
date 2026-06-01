"""Improved cache with TTL enforcement and memory leak prevention."""

import logging
from time import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ExpiringDict:
    """In-memory dictionary with TTL-based automatic expiration.
    
    Features:
    - Automatic cleanup of expired entries
    - Configurable cleanup interval
    - Memory efficient (removes stale data periodically)
    - Thread-safe for basic operations
    """
    
    def __init__(self, cleanup_interval: int = 300):
        """Initialize expiring dictionary.
        
        Args:
            cleanup_interval: Seconds between cleanup runs (default: 5 minutes)
        """
        self._data: dict[str, Tuple[str, float]] = {}  # key -> (value, expiry_time)
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time()
    
    def get(self, key: str) -> Optional[str]:
        """Get value if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Value if exists and not expired, None otherwise
        """
        self._cleanup_if_needed()
        
        if key in self._data:
            value, expiry = self._data[key]
            if time() < expiry:
                return value
            else:
                # Expired, delete it
                del self._data[key]
                logger.debug(f"Expired cache entry removed: {key}")
        
        return None
    
    def set(self, key: str, value: str, ttl: int) -> None:
        """Set value with TTL.
        
        Args:
            key: Cache key
            value: Cache value
            ttl: Time-to-live in seconds
        """
        expiry = time() + ttl
        self._data[key] = (value, expiry)
        
        # Warn if cache is getting too large
        if len(self._data) > 5000:
            logger.warning(f"Cache size exceeds 5000 entries: {len(self._data)}")
    
    def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    def _cleanup_if_needed(self) -> None:
        """Periodically remove expired entries."""
        now = time()
        if now - self._last_cleanup > self._cleanup_interval:
            expired = [k for k, (v, exp) in self._data.items() if exp < now]
            for k in expired:
                del self._data[k]
            
            if expired:
                logger.info(f"Cache cleanup: removed {len(expired)} expired entries, "
                           f"cache size now: {len(self._data)}")
            
            self._last_cleanup = now
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._data.clear()
        logger.info("Cache cleared")
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._data),
            "last_cleanup": self._last_cleanup,
        }


# Global instances
_expiring_memory_cache = ExpiringDict(cleanup_interval=300)
_stats = {"hits": 0, "misses": 0}


def get_memory_cache() -> ExpiringDict:
    """Get the global memory cache instance."""
    return _expiring_memory_cache


def memory_cache_get(key: str) -> Optional[str]:
    """Get value from memory cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None
    """
    value = _expiring_memory_cache.get(key)
    if value:
        _stats["hits"] += 1
        logger.debug(f"Memory cache hit: {key}")
    else:
        _stats["misses"] += 1
    return value


def memory_cache_set(key: str, value: str, ttl: int = 3600) -> None:
    """Set value in memory cache with TTL.
    
    Args:
        key: Cache key
        value: Cache value
        ttl: Time-to-live in seconds
    """
    _expiring_memory_cache.set(key, value, ttl)
    logger.debug(f"Memory cache set: {key} (TTL: {ttl}s)")


def memory_cache_delete(key: str) -> bool:
    """Delete key from memory cache.
    
    Args:
        key: Cache key to delete
        
    Returns:
        True if deleted, False if not found
    """
    return _expiring_memory_cache.delete(key)


def memory_cache_stats() -> dict:
    """Get memory cache statistics."""
    return {
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_ratio": _stats["hits"] / max(1, _stats["hits"] + _stats["misses"]),
        "size": len(_expiring_memory_cache._data),
    }
