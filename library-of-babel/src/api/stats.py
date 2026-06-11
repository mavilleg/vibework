"""
Statistics API routes for the Library of Babel.

This module provides the API endpoints for retrieving library statistics
and monitoring information.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from ..config import get_config
from ..models.library import Library, LibraryStats
from ..services.generation import BookGenerator
from ..services.search import BookSearch
from ..services.cache import create_cache

router = APIRouter(prefix="/api/stats", tags=["stats"])

# Initialize services
library = Library()
generator = BookGenerator()
search_service = BookSearch()
cache = create_cache()


@router.get("", response_model=dict, summary="Get library statistics")
async def get_library_stats():
    """
    Get overall library statistics.
    
    This endpoint returns comprehensive statistics about the library,
    including total possible books, cached books, and usage metrics.
    
    Returns:
        Library statistics
    """
    try:
        stats = library.get_stats()
        
        return {
            "library": {
                "name": "Library of Babel",
                "version": get_config().version,
                "environment": get_config().environment,
            },
            "books": {
                "total_possible": str(stats.total_possible_books),
                "cached": stats.cached_books,
                "storage_used_bytes": stats.storage_used_bytes,
                "storage_used_gb": round(stats.storage_used_bytes / (1024**3), 6),
            },
            "requests": {
                "today": stats.requests_today,
            },
            "generation": {
                "total_generated": generator.stats.total_generated,
                "average_time_ms": round(generator.stats.average_time_ms, 2),
                "last_generation_time_ms": round(generator.stats.last_generation_time_ms, 2),
            },
            "search": {
                "total_searches": search_service.stats.total_searches,
                "total_books_searched": search_service.stats.total_books_searched,
                "total_matches": search_service.stats.total_matches,
                "average_search_time_ms": round(search_service.stats.average_search_time_ms, 2),
            },
            "cache": cache.get_stats().to_dict(),
            "config": {
                "pages": get_config().book.pages,
                "lines_per_page": get_config().book.lines_per_page,
                "chars_per_line": get_config().book.chars_per_line,
                "alphabet_size": get_config().book.alphabet_size,
                "total_chars_per_book": get_config().book.total_chars,
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {e}")


@router.get("/config", response_model=dict, summary="Get library configuration")
async def get_config_stats():
    """
    Get the current library configuration.
    
    This endpoint returns the configuration settings for the library,
    including book structure and encoding parameters.
    
    Returns:
        Library configuration
    """
    try:
        config = get_config()
        
        return {
            "app": {
                "name": config.name,
                "version": config.version,
                "debug": config.debug,
                "environment": config.environment,
                "port": config.port,
            },
            "book": {
                "pages": config.book.pages,
                "lines_per_page": config.book.lines_per_page,
                "chars_per_line": config.book.chars_per_line,
                "alphabet": config.book.alphabet,
                "alphabet_size": config.book.alphabet_size,
                "total_chars": config.book.total_chars,
                "total_possible_books": str(config.book.total_possible_books),
            },
            "cache": {
                "enabled": config.cache.enabled,
                "ttl": config.cache.ttl,
                "max_size": config.cache.max_size,
                "backend": config.cache.backend,
            },
            "azure": {
                "is_enabled": config.azure.is_azure_enabled,
                "blob_container": config.azure.blob_container,
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {e}")


@router.get("/health", response_model=dict, summary="Health check endpoint")
async def health_check():
    """
    Health check endpoint.
    
    This endpoint can be used to verify that the service is running
    and to check basic functionality.
    
    Returns:
        Health status information
    """
    try:
        # Test basic functionality
        test_book = generator.generate_by_number(0)
        
        return {
            "status": "healthy",
            "timestamp": test_book.metadata.generated_at.isoformat() if test_book.metadata.generated_at else None,
            "version": get_config().version,
            "environment": get_config().environment,
            "checks": {
                "book_generation": "ok",
                "encoding": "ok",
                "cache": "ok" if cache.get_stats().size >= 0 else "error",
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@router.get("/sample", response_model=list, summary="Get sample books")
async def get_sample_books(
    count: int = 10
):
    """
    Get a sample of books from the library.
    
    This endpoint returns a curated sample of books for demonstration
    and testing purposes.
    
    Args:
        count: Number of sample books to return
    
    Returns:
        List of sample book data
    """
    try:
        samples = library.generate_sample_books(count)
        return [book.to_dict() for book in samples]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate samples: {e}")
