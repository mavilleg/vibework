"""Regression tests for previously identified issues."""

from src.main import app
from src.services.search import SearchStats


def _collect_paths(routes: list) -> list[str]:
    """Collect route paths from a list of routes.

    Handles both plain routes (which expose a ``path`` attribute directly) and
    FastAPI's ``_IncludedRouter`` wrapper objects (introduced in 0.137.x) which
    store the underlying ``APIRouter`` on ``original_router``.  The function
    recurses so that arbitrarily nested routers are handled correctly.
    """
    paths: list[str] = []
    for route in routes:
        if hasattr(route, "path"):
            paths.append(route.path)
        elif hasattr(route, "original_router") and hasattr(route.original_router, "routes"):
            paths.extend(_collect_paths(route.original_router.routes))
    return paths


def test_books_route_specific_paths_precede_dynamic_path() -> None:
    """Ensure fixed `/api/books` routes are matched before `/{book_id}`."""
    paths = _collect_paths(app.routes)

    dynamic_index = paths.index("/api/books/{book_id}")
    assert paths.index("/api/books/random") < dynamic_index
    assert paths.index("/api/books/range") < dynamic_index
    assert paths.index("/api/books/special") < dynamic_index


def test_search_stats_average_uses_time_ms() -> None:
    """Ensure average search time is computed from elapsed time, not books searched."""
    stats = SearchStats()
    stats.record_search(books_searched=100, matches=3, time_ms=40.0)
    stats.record_search(books_searched=1000, matches=10, time_ms=60.0)

    assert stats.total_time_ms == 100.0
    assert stats.average_search_time_ms == 50.0
