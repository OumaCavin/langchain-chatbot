"""
Redis Caching Module for Generic Chat Agent

Provides distributed caching, session storage, and response caching
for improved performance and scalability.

Author: MiniMax Agent
"""

import hashlib
import json
import os
from datetime import timedelta
from typing import Any, Optional
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCache:
    """
    Redis-based caching system for chatbot responses and session data.

    Features:
    - LLM response caching
    - Session state persistence
    - Rate limit tracking
    - TTL-based expiration
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: str = None,
        key_prefix: str = "chatbot:",
        default_ttl: int = 3600
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis host (defaults to REDIS_HOST env var or localhost)
            port: Redis port (defaults to REDIS_PORT env var or 6379)
            db: Redis database number
            password: Redis password (optional)
            key_prefix: Prefix for all keys
            default_ttl: Default time-to-live in seconds
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not installed. Install with: pip install redis")

        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = port or int(os.environ.get("REDIS_PORT", "6379"))
        self.db = db
        self.password = password or os.environ.get("REDIS_PASSWORD")
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

        self._client: Optional[redis.Redis] = None
        self._connected = False

    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self._client

    def connect(self) -> bool:
        """
        Test connection to Redis.

        Returns:
            True if connected, False otherwise
        """
        try:
            self.client.ping()
            self._connected = True
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self._connected:
            return False
        try:
            self.client.ping()
            return True
        except:
            self._connected = False
            return False

    def _make_key(self, *parts: str) -> str:
        """Create a prefixed cache key."""
        return self.key_prefix + ":".join(parts)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            value = self.client.get(self._make_key(key))
            if value:
                return json.loads(value)
            return None
        except (redis.RedisError, json.JSONDecodeError):
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            return self.client.setex(
                self._make_key(key),
                ttl,
                serialized
            )
        except (redis.RedisError, TypeError):
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(self.client.delete(self._make_key(key)))
        except redis.RedisError:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.client.exists(self._make_key(key)))
        except redis.RedisError:
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key."""
        try:
            return bool(self.client.expire(self._make_key(key), ttl))
        except redis.RedisError:
            return False

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter."""
        try:
            return self.client.incr(self._make_key(key), amount)
        except redis.RedisError:
            return None

    def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement a counter."""
        try:
            return self.client.decr(self._make_key(key), amount)
        except redis.RedisError:
            return None

    # Session management
    def save_session(
        self,
        session_id: str,
        session_data: dict,
        ttl: int = 86400
    ) -> bool:
        """
        Save session data.

        Args:
            session_id: Session identifier
            session_data: Session data dictionary
            ttl: Time-to-live in seconds (default: 24 hours)

        Returns:
            True if successful
        """
        return self.set(f"session:{session_id}", session_data, ttl)

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        return self.get(f"session:{session_id}")

    def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        return self.delete(f"session:{session_id}")

    def extend_session(self, session_id: str, ttl: int = 86400) -> bool:
        """Extend session TTL."""
        return self.expire(f"session:{session_id}", ttl)

    # Response caching
    def cache_response(
        self,
        prompt_hash: str,
        response: dict,
        ttl: int = 3600
    ) -> bool:
        """
        Cache LLM response.

        Args:
            prompt_hash: Hash of the prompt
            response: LLM response dictionary
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        return self.set(f"response:{prompt_hash}", response, ttl)

    def get_cached_response(self, prompt_hash: str) -> Optional[dict]:
        """Get cached LLM response."""
        return self.get(f"response:{prompt_hash}")

    def invalidate_response_cache(self, prompt_hash: str) -> bool:
        """Invalidate cached response."""
        return self.delete(f"response:{prompt_hash}")

    # Rate limiting with Redis
    def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window.

        Args:
            identifier: Rate limit identifier (IP, user ID, etc.)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        key = self._make_key(f"ratelimit:{identifier}")
        try:
            current = self.client.get(key)
            if current is None:
                self.client.setex(key, window_seconds, 1)
                return True, limit - 1

            current = int(current)
            if current >= limit:
                return False, 0

            self.client.incr(key)
            return True, limit - current - 1
        except redis.RedisError:
            return True, limit  # Fail open

    # Utility methods
    def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "session:*")

        Returns:
            Number of keys deleted
        """
        try:
            full_pattern = self._make_key(pattern)
            keys = self.client.keys(full_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            info = self.client.info()
            return {
                "connected": self.is_connected(),
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except redis.RedisError:
            return {"connected": False}

    def _calculate_hit_rate(self, info: dict) -> str:
        """Calculate cache hit rate."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return "0%"
        return f"{(hits / total * 100):.2f}%"


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache(
    host: str = None,
    port: int = None,
    db: int = 0,
    password: str = None
) -> RedisCache:
    """
    Get or create the global Redis cache instance.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password

    Returns:
        RedisCache instance
    """
    global _cache
    if _cache is None:
        _cache = RedisCache(host, port, db, password)
    return _cache


def cache_response(ttl: int = 3600):
    """
    Decorator to cache function responses.

    Args:
        ttl: Time-to-live in seconds

    Usage:
        @cache_response(ttl=1800)
        def expensive_function(arg1, arg2):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args if not isinstance(arg, self.__class__))
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            cache = get_cache()

            # Try to get cached result
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args if not isinstance(arg, self.__class__))
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            cache = get_cache()

            # Try to get cached result
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def generate_prompt_hash(messages: list, model: str = None) -> str:
    """
    Generate a hash for prompt caching.

    Args:
        messages: List of message dictionaries
        model: Model name to include in hash

    Returns:
        MD5 hash string
    """
    import json
    content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()
