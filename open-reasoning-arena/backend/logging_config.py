"""
Logging configuration for Open Reasoning Arena.

This module provides structured logging with JSON formatter for production
and human-readable formatter for development. It includes:
- Request ID tracking
- Correlation ID support
- Context-aware logging
- JSON and console formatters
"""

import json
import logging
import sys
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

from .config import get_config


# Thread-local storage for request context
_thread_local = threading.local()


class RequestContext:
    """Request context for logging."""
    
    def __init__(self):
        self.request_id: Optional[str] = None
        self.correlation_id: Optional[str] = None
        self.user_id: Optional[int] = None
        self.user_agent: Optional[str] = None
        self.ip_address: Optional[str] = None
        self.method: Optional[str] = None
        self.path: Optional[str] = None
        self.status_code: Optional[int] = None
        self.duration_ms: Optional[float] = None
        self.custom_fields: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        result = {}
        if self.request_id:
            result["request_id"] = self.request_id
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        if self.user_id:
            result["user_id"] = self.user_id
        if self.user_agent:
            result["user_agent"] = self.user_agent
        if self.ip_address:
            result["ip_address"] = self.ip_address
        if self.method:
            result["method"] = self.method
        if self.path:
            result["path"] = self.path
        if self.status_code:
            result["status_code"] = self.status_code
        if self.duration_ms:
            result["duration_ms"] = round(self.duration_ms, 3)
        result.update(self.custom_fields)
        return result


def get_context() -> RequestContext:
    """Get the current request context."""
    if not hasattr(_thread_local, "context"):
        _thread_local.context = RequestContext()
    return _thread_local.context


def set_context(**kwargs) -> None:
    """Set request context fields."""
    context = get_context()
    for key, value in kwargs.items():
        if hasattr(context, key):
            setattr(context, key, value)
        else:
            context.custom_fields[key] = value


def clear_context() -> None:
    """Clear the current request context."""
    if hasattr(_thread_local, "context"):
        delattr(_thread_local, "context")


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""
    return str(uuid.uuid4())


# ==================== FORMATTERS ====================

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_timestamp: bool = True, include_level: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add timestamp
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add log level
        if self.include_level:
            log_data["level"] = record.levelname
            log_data["level_num"] = record.levelno
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }
        
        # Add request context
        context = get_context()
        context_data = context.to_dict()
        if context_data:
            log_data["context"] = context_data
        
        # Add extra fields
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "asctime"
            ):
                try:
                    # Skip non-serializable objects
                    json.dumps(value)
                    extra_fields[key] = value
                except (TypeError, ValueError):
                    extra_fields[key] = str(value)
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for development."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        # Get base format
        base_msg = super().format(record)
        
        # Add request context
        context = get_context()
        context_parts = []
        if context.request_id:
            context_parts.append(f"request_id={context.request_id}")
        if context.correlation_id:
            context_parts.append(f"correlation_id={context.correlation_id[:8]}...")
        if context.user_id:
            context_parts.append(f"user_id={context.user_id}")
        
        if context_parts:
            return f"{base_msg} [{', '.join(context_parts)}]"
        
        return base_msg


# ==================== LOGGERS ====================

class StructuredLogger:
    """Logger with structured logging support."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def debug(self, msg: str, **kwargs) -> None:
        """Log debug message with extra fields."""
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs) -> None:
        """Log info message with extra fields."""
        self.logger.info(msg, extra=kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        """Log warning message with extra fields."""
        self.logger.warning(msg, extra=kwargs)
    
    def error(self, msg: str, **kwargs) -> None:
        """Log error message with extra fields."""
        self.logger.error(msg, extra=kwargs)
    
    def exception(self, msg: str, **kwargs) -> None:
        """Log exception with extra fields."""
        self.logger.exception(msg, extra=kwargs)
    
    def critical(self, msg: str, **kwargs) -> None:
        """Log critical message with extra fields."""
        self.logger.critical(msg, extra=kwargs)


# ==================== LOGGING CONFIGURATION ====================

def configure_logging() -> None:
    """Configure logging based on environment."""
    config = get_config()
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root logger level
    level = logging.DEBUG if config.debug else logging.INFO
    root_logger.setLevel(level)
    
    # Create formatter based on environment
    if config.environment == "production":
        formatter = JSONFormatter()
    else:
        formatter = ConsoleFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("prometheus_client").setLevel(logging.WARNING)
    
    # Configure uvicorn access logging
    if config.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger for a module."""
    return StructuredLogger(name)


# ==================== MIDDLEWARE ====================

class LoggingMiddleware:
    """ASGI middleware for request logging."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Generate request ID
        request_id = generate_request_id()
        
        # Extract correlation ID from headers
        correlation_id = None
        headers = dict(scope.get("headers", []))
        if b"x-correlation-id" in headers:
            correlation_id = headers[b"x-correlation-id"].decode()
        elif b"correlation-id" in headers:
            correlation_id = headers[b"correlation-id"].decode()
        
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Extract user agent and IP
        user_agent = headers.get(b"user-agent", b"").decode() or None
        ip_address = None
        if b"x-forwarded-for" in headers:
            ip_address = headers[b"x-forwarded-for"].decode().split(",")[0]
        elif b"x-real-ip" in headers:
            ip_address = headers[b"x-real-ip"].decode()
        
        # Set context
        set_context(
            request_id=request_id,
            correlation_id=correlation_id,
            user_agent=user_agent,
            ip_address=ip_address,
            method=scope["method"],
            path=scope["path"],
        )
        
        # Add correlation ID to response headers
        response_headers = {
            b"x-request-id": request_id.encode(),
            b"x-correlation-id": correlation_id.encode(),
        }
        
        start_time = time.time()
        status_code = None
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Add our headers
                for key, value in response_headers.items():
                    if key not in message.get("headers", {}):
                        message["headers"].append((key, value))
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            set_context(status_code=status_code, duration_ms=duration_ms)
            
            # Log request
            logger = get_logger("http")
            logger.info(
                f"{scope['method']} {scope['path']} {status_code}",
                method=scope["method"],
                path=scope["path"],
                status_code=status_code,
                duration_ms=round(duration_ms, 3),
            )
            
            # Clear context
            clear_context()


# ==================== INITIALIZATION ====================

import time  # Import here to avoid circular import

# Configure logging on import
configure_logging()

# Create a default logger
logger = get_logger(__name__)


# ==================== EXPORTS ====================

__all__ = [
    "configure_logging",
    "get_logger",
    "StructuredLogger",
    "LoggingMiddleware",
    "get_context",
    "set_context",
    "clear_context",
    "generate_request_id",
    "generate_correlation_id",
    "JSONFormatter",
    "ConsoleFormatter",
    "logger",
]
