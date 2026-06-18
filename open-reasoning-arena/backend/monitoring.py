"""
Monitoring and metrics for Open Reasoning Arena.

This module provides Prometheus metrics for tracking application performance,
request counts, error rates, and custom business metrics.
"""

import time
from typing import Optional, Callable, Any
from functools import wraps

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    start_http_server,
    REGISTRY,
)
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST

from .config import get_config


# ==================== METRICS DEFINITIONS ====================

# Application metrics
REQUEST_COUNT = Counter(
    "ora_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "ora_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

REQUEST_SIZE = Histogram(
    "ora_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
)

RESPONSE_SIZE = Histogram(
    "ora_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint", "status_code"],
    buckets=[100, 1000, 10000, 100000, 1000000],
)

# Database metrics
DB_QUERY_COUNT = Counter(
    "ora_db_queries_total",
    "Total number of database queries",
    ["operation", "model"],
)

DB_QUERY_DURATION = Histogram(
    "ora_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "model"],
    buckets=[0.001, 0.01, 0.1, 0.5, 1.0],
)

DB_CONNECTION_POOL = Gauge(
    "ora_db_connection_pool_size",
    "Current database connection pool size",
)

DB_CONNECTION_POOL_USAGE = Gauge(
    "ora_db_connection_pool_usage",
    "Current database connection pool usage",
)

# Cache metrics
CACHE_HITS = Counter(
    "ora_cache_hits_total",
    "Total number of cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "ora_cache_misses_total",
    "Total number of cache misses",
    ["cache_type"],
)

CACHE_SIZE = Gauge(
    "ora_cache_size",
    "Current cache size",
    ["cache_type"],
)

CACHE_EVICTIONS = Counter(
    "ora_cache_evictions_total",
    "Total number of cache evictions",
    ["cache_type"],
)

# Business metrics
TASK_CREATED = Counter(
    "ora_tasks_created_total",
    "Total number of tasks created",
    ["category", "difficulty"],
)

SOLUTION_CREATED = Counter(
    "ora_solutions_created_total",
    "Total number of solutions created",
    ["model_name"],
)

CHALLENGE_CREATED = Counter(
    "ora_challenges_created_total",
    "Total number of challenges created",
)

CHALLENGE_ACCEPTED = Counter(
    "ora_challenges_accepted_total",
    "Total number of challenges accepted",
)

CHALLENGE_REJECTED = Counter(
    "ora_challenges_rejected_total",
    "Total number of challenges rejected",
)

SCORE_CREATED = Counter(
    "ora_scores_created_total",
    "Total number of scores created",
)

USER_CREATED = Counter(
    "ora_users_created_total",
    "Total number of users created",
    ["is_human"],
)

# Error metrics
ERROR_COUNT = Counter(
    "ora_errors_total",
    "Total number of errors",
    ["error_type", "endpoint", "status_code"],
)

RATE_LIMIT_HITS = Counter(
    "ora_rate_limit_hits_total",
    "Total number of rate limit hits",
    ["endpoint", "limit_type"],
)

# Active users
ACTIVE_USERS = Gauge(
    "ora_active_users",
    "Number of active users in the system",
)

ACTIVE_MODELS = Gauge(
    "ora_active_models",
    "Number of unique models that have submitted solutions",
)

# Leaderboard metrics
LEADERBOARD_MODELS = Gauge(
    "ora_leaderboard_models_count",
    "Number of models on the leaderboard",
)

LEADERBOARD_TOP_SCORE = Gauge(
    "ora_leaderboard_top_score",
    "Top score on the leaderboard",
)


# Authentication metrics
AUTH_TOKEN_CREATED = Counter(
    "ora_auth_tokens_created_total",
    "Total number of authentication tokens created",
    ["token_type"],
)

AUTH_TOKEN_VALIDATED = Counter(
    "ora_auth_tokens_validated_total",
    "Total number of authentication tokens validated",
    ["token_type"],
)

AUTH_TOKEN_INVALIDATED = Counter(
    "ora_auth_tokens_invalidated_total",
    "Total number of authentication tokens invalidated",
    ["reason"],
)

AUTH_TOKEN_REFRESHED = Counter(
    "ora_auth_tokens_refreshed_total",
    "Total number of authentication tokens refreshed",
)

AUTH_LOGIN_ATTEMPTS = Counter(
    "ora_auth_login_attempts_total",
    "Total number of login attempts",
    ["status"],  # success, failure
)

AUTH_LOGIN_FAILURES = Counter(
    "ora_auth_login_failures_total",
    "Total number of login failures",
    ["reason"],  # user_not_found, invalid_password, user_inactive
)

AUTH_ACTIVE_SESSIONS = Gauge(
    "ora_auth_active_sessions",
    "Number of active authentication sessions",
)

AUTH_USERS_REGISTERED = Counter(
    "ora_auth_users_registered_total",
    "Total number of users registered",
)


# WebSocket metrics
WS_CONNECTIONS = Gauge(
    "ora_websocket_connections",
    "Number of active WebSocket connections",
)

WS_MESSAGES_SENT = Counter(
    "ora_websocket_messages_sent_total",
    "Total number of WebSocket messages sent",
)

WS_MESSAGES_RECEIVED = Counter(
    "ora_websocket_messages_received_total",
    "Total number of WebSocket messages received",
)

WS_ERRORS = Counter(
    "ora_websocket_errors_total",
    "Total number of WebSocket errors",
)


# ==================== MONITORING MIDDLEWARE ====================

class MonitoringMiddleware:
    """ASGI middleware for monitoring HTTP requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        method = scope["method"]
        path = scope["path"]
        
        # Extract endpoint name (first path segment)
        endpoint = path.split("/")[1] if path.split("/")[1] else "root"
        
        start_time = time.time()
        request_size = 0
        response_size = 0
        status_code = None
        
        async def send_wrapper(message):
            nonlocal response_size, status_code
            
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Count request
                REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
                
            if message["type"] == "http.response.body":
                response_size += len(message.get("body", b""))
                
            await send(message)
        
        try:
            # Track request size
            if scope.get("headers"):
                for header_name, header_value in scope["headers"]:
                    if header_name.lower() == b"content-length":
                        request_size = int(header_value.decode())
                        break
            
            # Record request size
            REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(request_size)
            
            await self.app(scope, receive, send_wrapper)
            
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
            ERROR_COUNT.labels(
                error_type=type(e).__name__,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            
            if status_code:
                RESPONSE_SIZE.labels(method=method, endpoint=endpoint, status_code=str(status_code)).observe(response_size)


# ==================== DECORATORS ====================

def track_db_query(operation: str, model: Optional[str] = None):
    """Decorator to track database query metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            label_model = model or func.__name__
            try:
                result = func(*args, **kwargs)
                DB_QUERY_COUNT.labels(operation=operation, model=label_model).inc()
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_DURATION.labels(operation=operation, model=label_model).observe(duration)
        return wrapper
    return decorator


def track_cache(cache_type: str):
    """Decorator to track cache operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # This would be called from cache methods
            return result
        return wrapper
    return decorator


# ==================== METRICS SERVER ====================

class MetricsServer:
    """Prometheus metrics server."""
    
    _instance = None
    _running = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def start(self, port: int = 9090, addr: str = "0.0.0.0"):
        """Start the metrics server."""
        if not self._running:
            start_http_server(port=port, addr=addr)
            self._running = True
            print(f"Prometheus metrics server started on {addr}:{port}")
    
    def stop(self):
        """Stop the metrics server."""
        # Prometheus client doesn't have a clean stop method
        # We just mark it as stopped
        self._running = False


# ==================== METRICS UTILITIES ====================

def increment_task_created(category: str, difficulty: int):
    """Increment task created counter."""
    TASK_CREATED.labels(category=category, difficulty=str(difficulty)).inc()


def increment_solution_created(model_name: str):
    """Increment solution created counter."""
    SOLUTION_CREATED.labels(model_name=model_name).inc()


def increment_challenge_created():
    """Increment challenge created counter."""
    CHALLENGE_CREATED.inc()


def increment_challenge_accepted():
    """Increment challenge accepted counter."""
    CHALLENGE_ACCEPTED.inc()


def increment_challenge_rejected():
    """Increment challenge rejected counter."""
    CHALLENGE_REJECTED.inc()


def increment_score_created():
    """Increment score created counter."""
    SCORE_CREATED.inc()


def increment_user_created(is_human: bool):
    """Increment user created counter."""
    USER_CREATED.labels(is_human=str(is_human)).inc()


def increment_rate_limit(endpoint: str, limit_type: str):
    """Increment rate limit hit counter."""
    RATE_LIMIT_HITS.labels(endpoint=endpoint, limit_type=limit_type).inc()


def increment_error(error_type: str, endpoint: str, status_code: str):
    """Increment error counter."""
    ERROR_COUNT.labels(error_type=error_type, endpoint=endpoint, status_code=status_code).inc()


def increment_auth_failure(reason: str, operation: str):
    """Increment authentication failure counter."""
    AUTH_LOGIN_FAILURES.labels(reason=reason).inc()
    AUTH_LOGIN_ATTEMPTS.labels(status="failure").inc()


def increment_auth_success(operation: str):
    """Increment authentication success counter."""
    AUTH_LOGIN_ATTEMPTS.labels(status="success").inc()


def set_active_users(count: int):
    """Set active users gauge."""
    ACTIVE_USERS.set(count)


def set_active_models(count: int):
    """Set active models gauge."""
    ACTIVE_MODELS.set(count)


def set_leaderboard_metrics(models_count: int, top_score: float):
    """Set leaderboard metrics."""
    LEADERBOARD_MODELS.set(models_count)
    LEADERBOARD_TOP_SCORE.set(top_score)


def set_cache_metrics(cache_type: str, size: int, hits: int, misses: int, evictions: int):
    """Set cache metrics."""
    CACHE_SIZE.labels(cache_type=cache_type).set(size)
    # Hits, misses, evictions are counters, not gauges
    # They are incremented separately


# ==================== INITIALIZATION ====================

def init_monitoring():
    """Initialize monitoring system."""
    config = get_config()
    
    # Start metrics server if monitoring is enabled
    if config.debug or config.environment != "production":
        # In development, start on default port
        MetricsServer().start(port=9090)
    
    # In production, metrics might be scraped by a sidecar
    # or we might not run the server at all
    
    print("Monitoring initialized")


def get_metrics_middleware():
    """Get the monitoring middleware."""
    return MonitoringMiddleware


# ==================== CUSTOM COLLECTORS ====================

class CustomMetricsCollector:
    """Custom metrics collector for business-specific metrics."""
    
    def collect(self):
        """Collect all custom metrics."""
        # This is where we would add custom metrics
        # For now, we just return the registry
        return REGISTRY


# Export for use in main.py
__all__ = [
    "MonitoringMiddleware",
    "MetricsServer",
    "init_monitoring",
    "get_metrics_middleware",
    "REQUEST_COUNT",
    "REQUEST_DURATION",
    "REQUEST_SIZE",
    "RESPONSE_SIZE",
    "DB_QUERY_COUNT",
    "DB_QUERY_DURATION",
    "CACHE_HITS",
    "CACHE_MISSES",
    "CACHE_SIZE",
    "CACHE_EVICTIONS",
    "TASK_CREATED",
    "SOLUTION_CREATED",
    "CHALLENGE_CREATED",
    "CHALLENGE_ACCEPTED",
    "CHALLENGE_REJECTED",
    "SCORE_CREATED",
    "USER_CREATED",
    "ERROR_COUNT",
    "RATE_LIMIT_HITS",
    "ACTIVE_USERS",
    "ACTIVE_MODELS",
    "LEADERBOARD_MODELS",
    "LEADERBOARD_TOP_SCORE",
    "increment_task_created",
    "increment_solution_created",
    "increment_challenge_created",
    "increment_challenge_accepted",
    "increment_challenge_rejected",
    "increment_score_created",
    "increment_user_created",
    "increment_rate_limit",
    "increment_error",
    "set_active_users",
    "set_active_models",
    "set_leaderboard_metrics",
    "set_cache_metrics",
    "track_db_query",
]
