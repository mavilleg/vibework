"""
Main application for the Library of Babel.

This module is the entry point for the FastAPI application that provides
the Library of Babel API.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import get_config, AppConfig
from .exceptions import LibraryOfBabelError
from .monitoring import (
    setup_monitoring, 
    monitoring_server, 
    MonitoredCache, 
    MonitoredBookGenerator,
    MonitoredSearch,
    monitor_api_request,
    API_REQUESTS,
    ERRORS_TOTAL
)
from .api import books_router, search_router, stats_router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
config: AppConfig = None
app: FastAPI = None

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    This handles startup and shutdown events for the application.
    """
    global config
    
    # Startup
    logger.info("Starting Library of Babel API...")
    config = get_config()
    
    # Setup monitoring
    setup_monitoring()
    
    logger.info(f"Configuration: {config.name} v{config.version}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Debug mode: {config.debug}")
    
    # Initialize services
    from .models.library import Library
    from .services.generation import BookGenerator
    from .services.cache import create_cache
    from .services.search import BookSearch
    
    # Create global instances
    library = Library()
    generator = BookGenerator()
    cache = create_cache()
    search_service = BookSearch()
    
    # Create monitored instances
    monitored_cache = MonitoredCache(cache, cache_type=config.cache.backend)
    monitored_generator = MonitoredBookGenerator(generator)
    monitored_search = MonitoredSearch(search_service)
    
    # Store in app state
    app.state.library = library
    app.state.generator = monitored_generator
    app.state.cache = monitored_cache
    app.state.search_service = monitored_search
    app.state.config = config
    
    logger.info("Services initialized")
    logger.info(f"Book configuration: {config.book.pages} pages, "
                f"{config.book.lines_per_page} lines/page, "
                f"{config.book.chars_per_line} chars/line")
    logger.info(f"Total possible books: {config.book.total_possible_books}")
    
    # Log security configuration
    logger.info(f"Rate limiting: {config.security.rate_limit}")
    logger.info(f"CORS origins: {config.security.cors_origins}")
    logger.info(f"Authentication enabled: {config.security.enable_auth}")
    
    # Log monitoring configuration
    logger.info(f"Prometheus enabled: {config.monitoring.prometheus_enabled}")
    logger.info(f"JSON logging: {config.monitoring.json_logging}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Library of Babel API...")
    logger.info("Cleanup complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    global config
    config = get_config()
    
    # Create FastAPI app
    app = FastAPI(
        title="Library of Babel API",
        description=(
            "A digital implementation of Jorge Luis Borges' Library of Babel. "
            "This API provides access to a library containing all possible books "
            "of a given format (410 pages × 40 lines × ~80 characters)."
        ),
        version=config.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Store limiter in app state
    app.state.limiter = limiter
    
    # Configure CORS with security settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.security.cors_origins,
        allow_credentials=config.security.cors_allow_credentials,
        allow_methods=config.security.cors_allow_methods,
        allow_headers=config.security.cors_allow_headers,
        max_age=600,
    )
    
    # Add security headers middleware
    if config.security.enable_security_headers:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Configure properly in production
        )
    
    # Add rate limiting middleware
    app.add_middleware(SlowAPIMiddleware)
    
    # Include API routers
    app.include_router(books_router)
    app.include_router(search_router)
    app.include_router(stats_router)
    
    # Add static files for frontend (if available)
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except Exception:
        pass
    
    # Global exception handlers
    @app.exception_handler(LibraryOfBabelError)
    async def library_of_babel_exception_handler(
        request: Request, exc: LibraryOfBabelError
    ) -> JSONResponse:
        """Handle LibraryOfBabelError exceptions."""
        ERRORS_TOTAL.labels(
            error_type=type(exc).__name__,
            endpoint=request.url.path
        ).inc()
        
        # In production, don't expose details
        if config.environment == "production" and not config.debug:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.code,
                    "message": exc.message,
                },
            )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        """Handle rate limit exceeded exceptions."""
        ERRORS_TOTAL.labels(
            error_type="RateLimitExceeded",
            endpoint=request.url.path
        ).inc()
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": str(exc.detail),
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        ERRORS_TOTAL.labels(
            error_type="RequestValidationError",
            endpoint=request.url.path
        ).inc()
        
        # In production, don't expose full validation details
        if config.environment == "production" and not config.debug:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                },
            )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Global exception handler."""
        ERRORS_TOTAL.labels(
            error_type=type(exc).__name__,
            endpoint=request.url.path
        ).inc()
        
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        # In production, don't expose internal error details
        if config.environment == "production" and not config.debug:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                },
            )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "type": type(exc).__name__,
            },
        )
    
    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with basic information."""
        return {
            "name": "Library of Babel API",
            "version": config.version,
            "description": (
                "A digital implementation of Jorge Luis Borges' Library of Babel. "
                "Explore the universe of all possible books."
            ),
            "docs": "/docs",
            "health": "/api/stats/health",
            "environment": config.environment,
        }
    
    # Redirect to docs
    @app.get("/explore", tags=["root"])
    async def explore():
        """Redirect to API documentation."""
        return {
            "message": "Explore the Library of Babel API",
            "documentation": "/docs",
            "endpoints": {
                "books": "/api/books",
                "search": "/api/search",
                "stats": "/api/stats",

            }
        }
    
    return app


# Create the application instance
app = create_app()

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=config.port,
        reload=config.debug,
        log_level="debug" if config.debug else "info",
        # Enable access logging
        access_log=True,
    )
