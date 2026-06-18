"""
Redis Cache Backend for Open Reasoning Arena.

This module provides a Redis-based cache implementation for production use,
replacing the in-memory cache for distributed deployments.

Features:
- Redis-based caching with TTL support
- Connection pooling
- Automatic reconnection
- Cache statistics tracking
- Thread-safe operations

Author: Vibe Code Agent
Created: 2026-06-18
"""

from __future__ import annotations

import json
import logging
import pickle
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union
from functools import wraps

import redis
from redis import Redis
from redis.exceptions import ConnectionError, RedisError

from .config import get_config
from .monitoring import (
    CACHE_EVICTIONS,
    CACHE_HITS,
    CACHE_MISSES,
    CACHE_SIZE,
    increment_error,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RedisCacheStats:
    """Statistics for Redis cache operations."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0
    gets: int = 0
    deletes: int = 0
    errors: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "sets": self.sets,
            "gets": self.gets,
            "deletes": self.deletes,
            "errors": self.errors,
        }


class RedisCache(Generic[T]):
    """
    Redis-based cache implementation.
    
    This cache provides a distributed caching solution using Redis,
    suitable for production deployments with multiple instances.
    
    Features:
    - Automatic connection management
    - Connection pooling
    - TTL support
    - Cache statistics
    - Automatic reconnection
    - Serialization support (JSON, pickle)
    """
    
    def __init__(
        self,
        name: str,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600,
        max_size: int = 10000,
        pool_size: int = 10,
        serialize: str = "json",
    ):
        """
        Initialize Redis cache.
        
        Args:
            name: Cache namespace/prefix
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            default_ttl: Default TTL in seconds
            max_size: Maximum cache size (approximate)
            pool_size: Connection pool size
            serialize: Serialization method ('json' or 'pickle')
        """
        self.name = name
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.serialize = serialize
        
        # Connection pool
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[Redis] = None
        
        # Statistics
        self.stats = RedisCacheStats()
        
        # Connect to Redis
        self._connect()
        
        logger.info(f"RedisCache '{name}' initialized at {host}:{port}/{db}")
    
    def _connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.pool_size if hasattr(self, 'pool_size') else 10,
                decode_responses=True,
            )
            self.client = Redis(connection_pool=self.pool)
            
            # Test connection
            self.client.ping()
            logger.info(f"RedisCache '{self.name}' connected successfully")
            
        except RedisError as e:
            logger.error(f"RedisCache '{self.name}' connection failed: {e}")
            self.client = None
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    def _reconnect(self) -> None:
        """Reconnect to Redis if connection is lost."""
        if self.client is None:
            self._connect()
        else:
            try:
                self.client.ping()
            except RedisError:
                logger.warning(f"RedisCache '{self.name}' reconnecting...")
                self._connect()
    
    def _get_key(self, key: str) -> str:
        """Get the full Redis key with namespace."""
        return f"{self.name}:{key}"
    
    def _serialize(self, value: Any) -> str:
        """Serialize a value for storage."""
        if self.serialize == "json":
            return json.dumps(value)
        elif self.serialize == "pickle":
            return pickle.dumps(value).hex()
        else:
            raise ValueError(f"Unknown serialization method: {self.serialize}")
    
    def _deserialize(self, value: str, default: Any = None) -> Any:
        """Deserialize a value from storage."""
        if value is None:
            return default
            
        if self.serialize == "json":
            return json.loads(value)
        elif self.serialize == "pickle":
            return pickle.loads(bytes.fromhex(value))
        else:
            raise ValueError(f"Unknown serialization method: {self.serialize}")
    
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            default: Default value if key not found
            
        Returns:
            The cached value or default
        """
        try:
            self._reconnect()
            if self.client is None:
                self.stats.errors += 1
                return default
            
            full_key = self._get_key(key)
            value = self.client.get(full_key)
            
            self.stats.gets += 1
            
            if value is None:
                self.stats.misses += 1
                CACHE_MISSES.labels(cache_type=self.name).inc()
                return default
            
            self.stats.hits += 1
            CACHE_HITS.labels(cache_type=self.name).inc()
            
            return self._deserialize(value, default)
            
        except RedisError as e:
            self.stats.errors += 1
            increment_error("RedisError", "cache_get", "500")
            logger.error(f"RedisCache '{self.name}' get error: {e}")
            return default
    
    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._reconnect()
            if self.client is None:
                self.stats.errors += 1
                return False
            
            full_key = self._get_key(key)
            serialized = self._serialize(value)
            expire = ttl if ttl is not None else self.default_ttl
            
            self.client.setex(full_key, expire, serialized)
            
            self.stats.sets += 1
            CACHE_SIZE.labels(cache_type=self.name).inc()
            
            return True
            
        except RedisError as e:
            self.stats.errors += 1
            increment_error("RedisError", "cache_set", "500")
            logger.error(f"RedisCache '{self.name}' set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if deleted, False if not found or error
        """
        try:
            self._reconnect()
            if self.client is None:
                self.stats.errors += 1
                return False
            
            full_key = self._get_key(key)
            result = self.client.delete(full_key)
            
            self.stats.deletes += 1
            if result > 0:
                CACHE_SIZE.labels(cache_type=self.name).dec()
            
            return result > 0
            
        except RedisError as e:
            self.stats.errors += 1
            increment_error("RedisError", "cache_delete", "500")
            logger.error(f"RedisCache '{self.name}' delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            self._reconnect()
            if self.client is None:
                return False
            
            full_key = self._get_key(key)
            return self.client.exists(full_key) > 0
            
        except RedisError as e:
            self.stats.errors += 1
            logger.error(f"RedisCache '{self.name}' exists error: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        Get the TTL of a cache key.
        
        Args:
            key: The cache key
            
        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        try:
            self._reconnect()
            if self.client is None:
                return -2
            
            full_key = self._get_key(key)
            return self.client.ttl(full_key)
            
        except RedisError as e:
            self.stats.errors += 1
            logger.error(f"RedisCache '{self.name}' ttl error: {e}")
            return -2
    
    def clear(self) -> bool:
        """
        Clear all keys in this cache namespace.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._reconnect()
            if self.client is None:
                return False
            
            # Find all keys with this namespace
            pattern = f"{self.name}:*"
            keys = self.client.keys(pattern)
            
            if keys:
                self.client.delete(*keys)
            
            CACHE_SIZE.labels(cache_type=self.name).set(0)
            return True
            
        except RedisError as e:
            self.stats.errors += 1
            logger.error(f"RedisCache '{self.name}' clear error: {e}")
            return False
    
    def size(self) -> int:
        """
        Get the number of keys in this cache namespace.
        
        Returns:
            Number of keys
        """
        try:
            self._reconnect()
            if self.client is None:
                return 0
            
            pattern = f"{self.name}:*"
            keys = self.client.keys(pattern)
            return len(keys) if keys else 0
            
        except RedisError as e:
            self.stats.errors += 1
            logger.error(f"RedisCache '{self.name}' size error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = self.stats.to_dict()
        stats["size"] = self.size()
        stats["connected"] = self.client is not None
        return stats
    
    def close(self) -> None:
        """Close the Redis connection."""
        if self.client is not None:
            self.client.close()
            self.client = None
        if self.pool is not None:
            self.pool.close()
            self.pool = None
        logger.info(f"RedisCache '{self.name}' closed")


# Singleton cache instances
_tasks_cache: Optional[RedisCache] = None
_solutions_cache: Optional[RedisCache] = None
_leaderboard_cache: Optional[RedisCache] = None


def get_redis_cache(name: str) -> RedisCache:
    """
    Get a Redis cache instance by name.
    
    Args:
        name: The cache name
        
    Returns:
        RedisCache instance
    """
    config = get_config()
    
    if config.cache.backend != "redis":
        logger.warning(f"Redis cache requested but backend is {config.cache.backend}")
        # Fall back to memory cache
        from .cache import get_cache
        return get_cache(name)
    
    cache_config = {
        "host": config.cache.redis_host or "localhost",
        "port": config.cache.redis_port or 6379,
        "db": config.cache.redis_db or 0,
        "password": config.cache.redis_password or None,
        "default_ttl": config.cache.ttl,
        "max_size": config.cache.max_size,
    }
    
    return RedisCache(name, **cache_config)


def get_tasks_cache() -> RedisCache:
    """Get the tasks cache instance."""
    global _tasks_cache
    if _tasks_cache is None:
        _tasks_cache = get_redis_cache("tasks")
    return _tasks_cache


def get_solutions_cache() -> RedisCache:
    """Get the solutions cache instance."""
    global _solutions_cache
    if _solutions_cache is None:
        _solutions_cache = get_redis_cache("solutions")
    return _solutions_cache


def get_leaderboard_cache() -> RedisCache:
    """Get the leaderboard cache instance."""
    global _leaderboard_cache
    if _leaderboard_cache is None:
        _leaderboard_cache = get_redis_cache("leaderboard")
    return _leaderboard_cache


# Update CacheConfig to include Redis settings
@dataclass
class RedisCacheConfig:
    """Redis cache configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    pool_size: int = 10
