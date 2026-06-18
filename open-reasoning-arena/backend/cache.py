"""
Caching service for Open Reasoning Arena.

This module provides caching implementations for storing frequently accessed
data like tasks, solutions, and leaderboard results.
"""

import time
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, TypeVar, Generic, Any
from collections import OrderedDict

from .config import get_config


T = TypeVar('T')
logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for the cache."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate": round(self.hit_rate, 4),
        }


class Cache(ABC, Generic[T]):
    """Abstract base class for caches."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[T]:
        """Get an item from the cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """Set an item in the cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an item from the cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all items from the cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if an item exists in the cache."""
        pass
    
    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        pass


class MemoryCache(Cache[T]):
    """
    In-memory cache implementation using OrderedDict for LRU eviction.
    
    This is a simple LRU (Least Recently Used) cache that stores items
    in memory. It's suitable for development and single-instance deployments.
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        """
        Initialize the memory cache.
        
        Args:
            max_size: Maximum number of items to store
            ttl: Time-to-live in seconds for cached items
        """
        self.max_size = max_size
        self.default_ttl = ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.stats = CacheStats(max_size=max_size)
    
    def get(self, key: str) -> Optional[T]:
        """
        Get an item from the cache.
        
        Args:
            key: The cache key
        
        Returns:
            The cached item or None if not found/expired
        """
        if key not in self._cache:
            self.stats.misses += 1
            return None
        
        item = self._cache[key]
        
        # Check if expired
        if item["expires_at"] and item["expires_at"] < time.time():
            self.delete(key)
            self.stats.misses += 1
            return None
        
        # Update access time and move to end (mark as recently used)
        self._cache.move_to_end(key)
        item["accessed_at"] = time.time()
        
        self.stats.hits += 1
        return item["value"]
    
    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """
        Set an item in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        # Evict if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict()
        
        expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
        
        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "accessed_at": time.time(),
            "created_at": time.time(),
        }
        
        # Move to end (mark as recently used)
        self._cache.move_to_end(key)
        self.stats.size = len(self._cache)
    
    def delete(self, key: str) -> None:
        """
        Delete an item from the cache.
        
        Args:
            key: The cache key
        """
        if key in self._cache:
            del self._cache[key]
            self.stats.size = len(self._cache)
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        self._cache.clear()
        self.stats.size = 0
        self.stats.hits = 0
        self.stats.misses = 0
        self.stats.evictions = 0
    
    def exists(self, key: str) -> bool:
        """
        Check if an item exists in the cache.
        
        Args:
            key: The cache key
        
        Returns:
            True if the item exists and is not expired
        """
        if key not in self._cache:
            return False
        
        item = self._cache[key]
        if item["expires_at"] and item["expires_at"] < time.time():
            self.delete(key)
            return False
        
        return True
    
    def _evict(self) -> None:
        """Evict the least recently used item (O(1) with OrderedDict)."""
        if not self._cache:
            return
        
        # Remove the first item (least recently used)
        oldest_key = next(iter(self._cache))
        del self._cache[oldest_key]
        self.stats.evictions += 1
        self.stats.size = len(self._cache)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self.stats.size = len(self._cache)
        return self.stats


# Singleton cache instance
_tasks_cache: Optional[MemoryCache] = None
_solutions_cache: Optional[MemoryCache] = None
_leaderboard_cache: Optional[MemoryCache] = None


def get_tasks_cache() -> MemoryCache:
    """Get or create the tasks cache."""
    global _tasks_cache
    if _tasks_cache is None:
        config = get_config()
        _tasks_cache = MemoryCache(
            max_size=config.cache.max_size,
            ttl=config.cache.ttl
        )
    return _tasks_cache


def get_solutions_cache() -> MemoryCache:
    """Get or create the solutions cache."""
    global _solutions_cache
    if _solutions_cache is None:
        config = get_config()
        _solutions_cache = MemoryCache(
            max_size=config.cache.max_size,
            ttl=config.cache.ttl
        )
    return _solutions_cache


def get_leaderboard_cache() -> MemoryCache:
    """Get or create the leaderboard cache."""
    global _leaderboard_cache
    if _leaderboard_cache is None:
        config = get_config()
        _leaderboard_cache = MemoryCache(
            max_size=config.cache.max_size // 10,  # Smaller cache for leaderboard
            ttl=config.cache.ttl // 6  # Shorter TTL for leaderboard
        )
    return _leaderboard_cache


def clear_all_caches() -> None:
    """Clear all caches."""
    global _tasks_cache, _solutions_cache, _leaderboard_cache
    if _tasks_cache:
        _tasks_cache.clear()
    if _solutions_cache:
        _solutions_cache.clear()
    if _leaderboard_cache:
        _leaderboard_cache.clear()
