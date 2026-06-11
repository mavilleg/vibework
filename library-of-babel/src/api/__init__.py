"""
API routes for the Library of Babel project.

This package contains the FastAPI route handlers for the Library of Babel API.
"""

from .books import router as books_router
from .search import router as search_router
from .stats import router as stats_router

__all__ = ["books_router", "search_router", "stats_router"]
