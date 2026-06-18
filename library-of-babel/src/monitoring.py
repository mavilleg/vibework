"""
Monitoring and observability for the Library of Babel project.

This module provides Prometheus metrics, structured logging, and monitoring
capabilities for the application.
"""

import time
import logging
import threading
from typing import Optional, Any, Dict
from contextlib import contextmanager

from prometheus_client import (
    start_http_server,
    Counter,
    Histogram,
    Gauge,
    Summary
)

from .config import get_config


# ============================================================================
# Prometheus Metrics
# ============================================================================

# Book generation metrics
BOOKS_GENERATED = Counter(
    'library_of_babel_books_generated_total',
    'Total number of books generated',
    ['generation_method']  # by_id, by_number, random
)

BOOK_GENERATION_TIME = Histogram(
    'library_of_babel_book_generation_seconds',
    'Time spent generating books',
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

BOOK_GENERATION_SIZE = Histogram(
    'library_of_babel_book_size_bytes',
    'Size of generated books in bytes',
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000]
)

# Cache metrics
CACHE_HITS = Counter(
    'library_of_babel_cache_hits_total',
    'Total cache hits',
    ['cache_type']  # memory, redis, azure
)

CACHE_MISSES = Counter(
    'library_of_babel_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

CACHE_EVICTIONS = Counter(
    'library_of_babel_cache_evictions_total',
    'Total cache evictions',
    ['cache_type']
)

CACHE_SIZE = Gauge(
    'library_of_babel_cache_size',
    'Current cache size',
    ['cache_type']
)

CACHE_LATENCY = Histogram(
    'library_of_babel_cache_operations_seconds',
    'Time spent on cache operations',
    ['operation', 'cache_type'],  # get, set, delete
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1]
)

# API metrics
API_REQUESTS = Counter(
    'library_of_babel_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

API_REQUEST_LATENCY = Histogram(
    'library_of_babel_api_request_latency_seconds',
    'API request latency',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ACTIVE_REQUESTS = Gauge(
    'library_of_babel_active_requests',
    'Number of active API requests'
)

# Search metrics
SEARCH_QUERIES = Counter(
    'library_of_babel_search_queries_total',
    'Total search queries',
    ['strategy']  # sequential, random, smart, regex
)

SEARCH_LATENCY = Histogram(
    'library_of_babel_search_latency_seconds',
    'Search query latency',
    ['strategy'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

SEARCH_RESULTS = Histogram(
    'library_of_babel_search_results_count',
    'Number of search results returned',
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

# Error metrics
ERRORS_TOTAL = Counter(
    'library_of_babel_errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)


# ============================================================================
# Monitoring Server
# ============================================================================

class MonitoringServer:
    """Manages the Prometheus metrics server."""
    
    _instance = None
    _lock = threading.Lock()
    _started = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._started:
            self.config = get_config()
            self.port = self.config.monitoring.prometheus_port
            self.enabled = self.config.monitoring.prometheus_enabled
            self._started = True
    
    def start(self):
        """Start the Prometheus metrics server."""
        if self.enabled and not hasattr(self, '_server'):
            start_http_server(self.port)
            self._server = True
            logging.info(f"Prometheus metrics server started on port {self.port}")
    
    def stop(self):
        """Stop the Prometheus metrics server."""
        # Prometheus server doesn't have a clean stop method
        # This is a limitation of the prometheus_client library
        pass


# Singleton instance
monitoring_server = MonitoringServer()


# ============================================================================
# Structured Logging
# ============================================================================

class StructuredLogger:
    """Provides structured JSON logging."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.config = get_config()
        
        if self.config.monitoring.json_logging:
            self._setup_json_logging()
    
    def _setup_json_logging(self):
        """Configure JSON logging format."""
        try:
            from pythonjsonlogger import jsonlogger
            
            # Remove existing handlers
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
            
            # Add JSON handler
            json_handler = logging.StreamHandler()
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(levelname)s %(name)s %(message)s '
                '%(funcName)s %(lineno)d %(pathname)s'
            )
            json_handler.setFormatter(formatter)
            self.logger.addHandler(json_handler)
            
            # Set log level from config
            level = getattr(logging, self.config.monitoring.log_level.upper(), logging.INFO)
            self.logger.setLevel(level)
            
        except ImportError:
            # Fall back to standard logging if pythonjsonlogger not available
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def info(self, message: str, **kwargs):
        """Log info message with additional context."""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with additional context."""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with additional context."""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with additional context."""
        if kwargs:
            message = f"{message} | {kwargs}"
        self.logger.debug(message, extra=kwargs)


# Create module-level logger
logger = StructuredLogger(__name__)


# ============================================================================
# Monitoring Decorators and Context Managers
# ============================================================================

def monitor_api_request(method: str, endpoint: str):
    """Decorator to monitor API requests."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            ACTIVE_REQUESTS.inc()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                status_code = 200
                return result
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                ERRORS_TOTAL.labels(
                    error_type=type(e).__name__,
                    endpoint=endpoint
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                API_REQUESTS.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=str(status_code)
                ).inc()
                API_REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                ACTIVE_REQUESTS.dec()
        
        return wrapper
    return decorator


@contextmanager
def monitor_operation(operation: str, **labels):
    """Context manager to monitor operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        # You can add custom metrics here based on operation type
        logger.debug(f"Operation {operation} completed in {duration:.4f}s", 
                    extra={**labels, "duration": duration})


# ============================================================================
# Cache Monitoring Wrapper
# ============================================================================

class MonitoredCache:
    """Wrapper for cache with monitoring capabilities."""
    
    def __init__(self, cache, cache_type: str = "memory"):
        self.cache = cache
        self.cache_type = cache_type
    
    def get(self, key: str):
        """Get item from cache with monitoring."""
        start_time = time.time()
        try:
            result = self.cache.get(key)
            if result:
                CACHE_HITS.labels(self.cache_type).inc()
            else:
                CACHE_MISSES.labels(self.cache_type).inc()
            
            CACHE_SIZE.labels(self.cache_type).set(
                self.cache.get_stats().size
            )
            
            CACHE_LATENCY.labels(
                operation="get",
                cache_type=self.cache_type
            ).observe(time.time() - start_time)
            
            return result
        except Exception as e:
            logger.error(f"Cache get error: {e}", 
                        extra={"cache_type": self.cache_type, "key": key})
            raise
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set item in cache with monitoring."""
        start_time = time.time()
        try:
            self.cache.set(key, value, ttl)
            CACHE_SIZE.labels(self.cache_type).set(
                self.cache.get_stats().size
            )
            CACHE_LATENCY.labels(
                operation="set",
                cache_type=self.cache_type
            ).observe(time.time() - start_time)
        except Exception as e:
            logger.error(f"Cache set error: {e}", 
                        extra={"cache_type": self.cache_type, "key": key})
            raise
    
    def delete(self, key: str):
        """Delete item from cache with monitoring."""
        start_time = time.time()
        try:
            self.cache.delete(key)
            CACHE_SIZE.labels(self.cache_type).set(
                self.cache.get_stats().size
            )
            CACHE_LATENCY.labels(
                operation="delete",
                cache_type=self.cache_type
            ).observe(time.time() - start_time)
        except Exception as e:
            logger.error(f"Cache delete error: {e}", 
                        extra={"cache_type": self.cache_type, "key": key})
            raise
    
    def clear(self):
        """Clear cache with monitoring."""
        try:
            self.cache.clear()
            CACHE_SIZE.labels(self.cache_type).set(0)
        except Exception as e:
            logger.error(f"Cache clear error: {e}", 
                        extra={"cache_type": self.cache_type})
            raise
    
    def exists(self, key: str) -> bool:
        """Check if item exists in cache."""
        return self.cache.exists(key)
    
    def get_stats(self):
        """Get cache statistics."""
        return self.cache.get_stats()


# ============================================================================
# Book Generation Monitoring
# ============================================================================

class MonitoredBookGenerator:
    """Wrapper for book generator with monitoring."""
    
    def __init__(self, generator):
        self.generator = generator
    
    def generate_by_id(self, book_id: str):
        """Generate book by ID with monitoring."""
        start_time = time.time()
        try:
            book = self.generator.generate_by_id(book_id)
            BOOKS_GENERATED.labels('by_id').inc()
            BOOK_GENERATION_TIME.observe(time.time() - start_time)
            BOOK_GENERATION_SIZE.observe(len(book.content.encode('utf-8')))
            return book
        except Exception as e:
            ERRORS_TOTAL.labels(
                error_type=type(e).__name__,
                endpoint='generate_by_id'
            ).inc()
            raise
    
    def generate_by_number(self, book_number: int):
        """Generate book by number with monitoring."""
        start_time = time.time()
        try:
            book = self.generator.generate_by_number(book_number)
            BOOKS_GENERATED.labels('by_number').inc()
            BOOK_GENERATION_TIME.observe(time.time() - start_time)
            BOOK_GENERATION_SIZE.observe(len(book.content.encode('utf-8')))
            return book
        except Exception as e:
            ERRORS_TOTAL.labels(
                error_type=type(e).__name__,
                endpoint='generate_by_number'
            ).inc()
            raise
    
    def generate_random(self):
        """Generate random book with monitoring."""
        start_time = time.time()
        try:
            book = self.generator.generate_random()
            BOOKS_GENERATED.labels('random').inc()
            BOOK_GENERATION_TIME.observe(time.time() - start_time)
            BOOK_GENERATION_SIZE.observe(len(book.content.encode('utf-8')))
            return book
        except Exception as e:
            ERRORS_TOTAL.labels(
                error_type=type(e).__name__,
                endpoint='generate_random'
            ).inc()
            raise
    
    def get_generation_stats(self):
        """Get generation statistics."""
        return self.generator.get_generation_stats()
    
    def reset_stats(self):
        """Reset generation statistics."""
        self.generator.reset_stats()


# ============================================================================
# Search Monitoring
# ============================================================================

class MonitoredSearch:
    """Wrapper for search service with monitoring."""
    
    def __init__(self, search_service):
        self.search_service = search_service
    
    def search(self, query: str, limit: int = 10, strategy: str = "sequential"):
        """Search with monitoring."""
        start_time = time.time()
        try:
            results = self.search_service.search(query, limit, strategy)
            SEARCH_QUERIES.labels(strategy).inc()
            SEARCH_LATENCY.labels(strategy).observe(time.time() - start_time)
            SEARCH_RESULTS.observe(len(results))
            return results
        except Exception as e:
            ERRORS_TOTAL.labels(
                error_type=type(e).__name__,
                endpoint='search'
            ).inc()
            raise
    
    def search_regex(self, pattern: str, limit: int = 10):
        """Regex search with monitoring."""
        start_time = time.time()
        try:
            results = self.search_service.search_regex(pattern, limit)
            SEARCH_QUERIES.labels('regex').inc()
            SEARCH_LATENCY.labels('regex').observe(time.time() - start_time)
            SEARCH_RESULTS.observe(len(results))
            return results
        except Exception as e:
            ERRORS_TOTAL.labels(
                error_type=type(e).__name__,
                endpoint='search_regex'
            ).inc()
            raise


# ============================================================================
# Utility Functions
# ============================================================================

def setup_monitoring():
    """Setup monitoring for the application."""
    config = get_config()
    
    # Start Prometheus server if enabled
    if config.monitoring.prometheus_enabled:
        monitoring_server.start()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.monitoring.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # If JSON logging is enabled, reconfigure
    if config.monitoring.json_logging:
        try:
            from pythonjsonlogger import jsonlogger
            handler = logging.StreamHandler()
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(levelname)s %(name)s %(message)s '
                '%(funcName)s %(lineno)d %(pathname)s'
            )
            handler.setFormatter(formatter)
            logging.getLogger().handlers.clear()
            logging.getLogger().addHandler(handler)
        except ImportError:
            pass


def get_monitoring_status() -> Dict[str, Any]:
    """Get current monitoring status."""
    return {
        "prometheus_enabled": get_config().monitoring.prometheus_enabled,
        "prometheus_port": get_config().monitoring.prometheus_port,
        "json_logging": get_config().monitoring.json_logging,
        "log_level": get_config().monitoring.log_level
    }
