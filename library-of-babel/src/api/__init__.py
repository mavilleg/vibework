"""
API routers for the Library of Babel.

This package contains all the API route definitions.
"""

from .books import router as books_router
from .search import router as search_router
from .stats import router as stats_router

__all__ = ["books_router", "search_router", "stats_router"]
