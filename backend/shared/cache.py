"""
Redis cache client for LLM response caching.
"""
import json
import hashlib
from typing import Optional, Any
import redis.asyncio as redis

from shared.config import settings

# Global Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    # Test connection
    await redis_client.ping()


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()


def get_cache_key(content: str, prefix: str = "llm_cache") -> str:
    """Generate cache key from content hash."""
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return f"{prefix}:{content_hash}"


async def get_cached(key: str) -> Optional[Any]:
    """Get cached value by key."""
    if not redis_client:
        return None
    
    value = await redis_client.get(key)
    if value:
        return json.loads(value)
    return None


async def set_cached(key: str, value: Any, ttl: Optional[int] = None):
    """Set cached value with optional TTL in seconds."""
    if not redis_client:
        return
    
    serialized = json.dumps(value)
    if ttl:
        await redis_client.setex(key, ttl, serialized)
    else:
        await redis_client.set(key, serialized)


async def delete_cached(key: str):
    """Delete cached value by key."""
    if not redis_client:
        return
    
    await redis_client.delete(key)


async def clear_cache_prefix(prefix: str):
    """Clear all cached values with given prefix."""
    if not redis_client:
        return
    
    async for key in redis_client.scan_iter(f"{prefix}:*"):
        await redis_client.delete(key)
