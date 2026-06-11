"""
Main application for the Library of Babel.

This module is the entry point for the FastAPI application that provides
the Library of Babel API.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_config, AppConfig
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
    
    logger.info(f"Configuration: {config.name} v{config.version}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Debug mode: {config.debug}")
    
    # Initialize services
    from .models.library import Library
    from .services.generation import BookGenerator
    from .services.cache import create_cache
    
    # Create global instances
    library = Library()
    generator = BookGenerator()
    cache = create_cache()
    
    logger.info("Services initialized")
    logger.info(f"Book configuration: {config.book.pages} pages, "
                f"{config.book.lines_per_page} lines/page, "
                f"{config.book.chars_per_line} chars/line")
    logger.info(f"Total possible books: {config.book.total_possible_books}")
    
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
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(books_router)
    app.include_router(search_router)
    app.include_router(stats_router)
    
    # Add static files for frontend (if available)
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except Exception:
        pass
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if config.debug else "An unexpected error occurred",
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
    )
