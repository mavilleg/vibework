"""
Caching service for the Library of Babel.

This module provides caching implementations for storing frequently accessed books,
reducing generation time and improving performance.
"""

import time
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, TypeVar, Generic

from ..config import get_config
from ..models.book import Book


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


class BookCache(ABC, Generic[T]):
    """
    Abstract base class for book caches.
    
    This defines the interface for caching implementations.
    """
    
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


class MemoryCache(BookCache[T]):
    """
    In-memory cache implementation.
    
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
        self._cache: Dict[str, Dict[str, any]] = {}
        self._access_order: list[str] = []
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
        
        # Update access time and move to end of access order
        self._access_order.remove(key)
        self._access_order.append(key)
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
        
        if key not in self._access_order:
            self._access_order.append(key)
        
        self.stats.size = len(self._cache)
    
    def delete(self, key: str) -> None:
        """
        Delete an item from the cache.
        
        Args:
            key: The cache key
        """
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            self.stats.size = len(self._cache)
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        self._cache.clear()
        self._access_order.clear()
        self.stats.size = 0
    
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
        """Evict the least recently used item."""
        if not self._access_order:
            return
        
        # Remove the first item (least recently used)
        oldest_key = self._access_order.pop(0)
        if oldest_key in self._cache:
            del self._cache[oldest_key]
            self.stats.evictions += 1
            self.stats.size = len(self._cache)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self.stats.size = len(self._cache)
        return self.stats


class RedisCache(BookCache[T]):
    """
    Redis-based cache implementation.
    
    This cache uses Azure Cache for Redis to store items, providing
    distributed caching for multi-instance deployments.
    """
    
    def __init__(self, connection_string: Optional[str] = None, 
                 max_size: int = 10000, ttl: int = 3600) -> None:
        """
        Initialize the Redis cache.
        
        Args:
            connection_string: Redis connection string
            max_size: Maximum number of items to store (approximate)
            ttl: Time-to-live in seconds for cached items
        """
        self.max_size = max_size
        self.default_ttl = ttl
        self.stats = CacheStats(max_size=max_size)
        
        # Try to import redis
        try:
            import redis
            self.redis = redis
        except ImportError:
            raise ImportError("redis package is required for RedisCache")
        
        # Get connection string from config or parameter
        config = get_config()
        connection_string = connection_string or config.azure.redis_connection_string
        
        if not connection_string:
            raise ValueError("Redis connection string is required")
        
        # Parse connection string
        self.client = self._create_client(connection_string)
    
    def _create_client(self, connection_string: str):
        """Create Redis client from connection string."""
        # Parse connection string
        # Format: redis://:password@host:port/0?ssl=True
        if connection_string.startswith("redis://"):
            # Use Redis from redis-py
            return self.redis.Redis.from_url(connection_string)
        else:
            # Try to parse as host:port
            parts = connection_string.split(":")
            if len(parts) == 2:
                return self.redis.Redis(host=parts[0], port=int(parts[1]))
            else:
                return self.redis.Redis(host=connection_string)
    
    def get(self, key: str) -> Optional[T]:
        """
        Get an item from the cache.
        
        Args:
            key: The cache key
        
        Returns:
            The cached item or None if not found/expired
        """
        try:
            value = self.client.get(key)
            if value is None:
                self.stats.misses += 1
                return None
            
            self.stats.hits += 1
            return self._deserialize(value)
            
        except Exception as e:
            logger.warning("Redis cache get failed for key %s: %s", key, e)
            self.stats.misses += 1
            return None
    
    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """
        Set an item in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        try:
            serialized = self._serialize(value)
            self.client.setex(key, ttl or self.default_ttl, serialized)
            self.stats.size = self.client.dbsize()
        except Exception as e:
            logger.warning("Redis cache set failed for key %s: %s", key, e)
    
    def delete(self, key: str) -> None:
        """
        Delete an item from the cache.
        
        Args:
            key: The cache key
        """
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning("Redis cache delete failed for key %s: %s", key, e)
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        try:
            self.client.flushdb()
            self.stats.size = 0
        except Exception as e:
            logger.warning("Redis cache clear failed: %s", e)
    
    def exists(self, key: str) -> bool:
        """
        Check if an item exists in the cache.
        
        Args:
            key: The cache key
        
        Returns:
            True if the item exists and is not expired
        """
        try:
            return self.client.exists(key) == 1
        except Exception as e:
            logger.warning("Redis cache exists check failed for key %s: %s", key, e)
            return False
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        try:
            self.stats.size = self.client.dbsize()
        except Exception as e:
            logger.warning("Redis cache stats retrieval failed: %s", e)
        return self.stats
    
    def _serialize(self, value: T) -> bytes:
        """Serialize a value for storage in Redis."""
        if isinstance(value, Book):
            payload = {"__type__": "Book", "data": value.to_dict()}
        else:
            payload = {"__type__": "generic", "data": value}
        try:
            return json.dumps(payload).encode("utf-8")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Value for Redis cache key is not JSON-serializable: {e}") from e
    
    def _deserialize(self, data: bytes) -> T:
        """Deserialize a value from Redis."""
        payload = json.loads(data.decode("utf-8"))
        if "__type__" not in payload or "data" not in payload:
            raise ValueError("Invalid Redis cache payload format")

        value_type = payload.get("__type__")
        if value_type == "Book":
            return Book.from_dict(payload["data"])
        return payload["data"]


class AzureBlobCache(BookCache[Book]):
    """
    Azure Blob Storage cache implementation.
    
    This cache stores books as JSON files in Azure Blob Storage,
    providing persistent storage for frequently accessed books.
    """
    
    def __init__(self, connection_string: Optional[str] = None,
                 container_name: str = "books", ttl: int = 86400) -> None:
        """
        Initialize the Azure Blob cache.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Name of the blob container
            ttl: Time-to-live in seconds for cached items
        """
        self.container_name = container_name
        self.default_ttl = ttl
        self.stats = CacheStats()
        
        # Try to import Azure Blob Storage client
        try:
            from azure.storage.blob import BlobServiceClient
            self.BlobServiceClient = BlobServiceClient
        except ImportError:
            raise ImportError("azure-storage-blob package is required for AzureBlobCache")
        
        # Get connection string from config or parameter
        config = get_config()
        connection_string = connection_string or config.azure.storage_connection_string
        
        if not connection_string:
            raise ValueError("Azure Storage connection string is required")
        
        self.client = self.BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            self.container_client.create_container()
        except Exception:
            # Container probably already exists
            pass
    
    def get(self, key: str) -> Optional[Book]:
        """
        Get a book from the cache.
        
        Args:
            key: The book ID
        
        Returns:
            The cached Book or None if not found/expired
        """
        try:
            blob_client = self.container_client.get_blob_client(key)
            blob = blob_client.download_blob()
            content = blob.readall().decode('utf-8')
            
            # Deserialize the book
            import json
            data = json.loads(content)
            book = Book.from_dict(data)
            
            self.stats.hits += 1
            return book
            
        except Exception as e:
            logger.warning("Azure blob cache get failed for key %s: %s", key, e)
            self.stats.misses += 1
            return None
    
    def set(self, key: str, value: Book, ttl: Optional[int] = None) -> None:
        """
        Set a book in the cache.
        
        Args:
            key: The book ID
            value: The Book to cache
            ttl: Time-to-live in seconds (not implemented for blob storage)
        """
        try:
            # Serialize the book
            import json
            content = json.dumps(value.to_dict(), indent=2)
            
            # Upload to blob storage
            blob_client = self.container_client.get_blob_client(key)
            blob_client.upload_blob(content, overwrite=True)
            
            self.stats.size = self.container_client.get_container_properties().blob_count
            
        except Exception as e:
            logger.warning("Azure blob cache set failed for key %s: %s", key, e)
    
    def delete(self, key: str) -> None:
        """
        Delete a book from the cache.
        
        Args:
            key: The book ID
        """
        try:
            blob_client = self.container_client.get_blob_client(key)
            blob_client.delete_blob()
        except Exception as e:
            logger.warning("Azure blob cache delete failed for key %s: %s", key, e)
    
    def clear(self) -> None:
        """Clear all books from the cache."""
        try:
            # List and delete all blobs
            blob_list = self.container_client.list_blobs()
            for blob in blob_list:
                blob_client = self.container_client.get_blob_client(blob.name)
                blob_client.delete_blob()
            self.stats.size = 0
        except Exception as e:
            logger.warning("Azure blob cache clear failed: %s", e)
    
    def exists(self, key: str) -> bool:
        """
        Check if a book exists in the cache.
        
        Args:
            key: The book ID
        
        Returns:
            True if the book exists
        """
        try:
            blob_client = self.container_client.get_blob_client(key)
            return blob_client.exists()
        except Exception as e:
            logger.warning("Azure blob cache exists check failed for key %s: %s", key, e)
            return False
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        try:
            self.stats.size = self.container_client.get_container_properties().blob_count
        except Exception as e:
            logger.warning("Azure blob cache stats retrieval failed: %s", e)
        return self.stats


def create_cache() -> BookCache[Book]:
    """
    Factory function to create the appropriate cache based on configuration.
    
    Returns:
        A BookCache instance
    """
    config = get_config()
    cache_config = config.cache
    
    if not cache_config.enabled:
        # Return a no-op cache
        class NoOpCache(BookCache[Book]):
            def get(self, key: str) -> Optional[Book]:
                return None
            def set(self, key: str, value: Book, ttl: Optional[int] = None) -> None:
                pass
            def delete(self, key: str) -> None:
                pass
            def clear(self) -> None:
                pass
            def exists(self, key: str) -> bool:
                return False
            def get_stats(self) -> CacheStats:
                return CacheStats()
        
        return NoOpCache()
    
    if cache_config.backend == "redis":
        try:
            return RedisCache()
        except Exception as e:
            logger.warning("Redis cache unavailable, falling back to memory cache: %s", e)
            # Fall back to memory cache
            pass
    
    if cache_config.backend == "azure":
        try:
            return AzureBlobCache()
        except Exception as e:
            logger.warning("Azure blob cache unavailable, falling back to memory cache: %s", e)
            # Fall back to memory cache
            pass
    
    # Default to memory cache
    return MemoryCache(max_size=cache_config.max_size, ttl=cache_config.ttl)
