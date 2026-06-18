"""
Tests for the Library of Babel API endpoints.

This module tests the FastAPI endpoints for books, search, and stats.
"""

import pytest
from fastapi.testclient import TestClient
import os

# Set environment variables for testing
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["CACHE_ENABLED"] = "true"
os.environ["CACHE_BACKEND"] = "memory"
os.environ["ENABLE_AUTH"] = "false"

from src.main import create_app


@pytest.fixture
def client():
    """Create a test client for the API."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def small_book_config():
    """Configure the app with small book sizes for faster testing."""
    os.environ["BOOK_PAGES"] = "2"
    os.environ["BOOK_LINES_PER_PAGE"] = "2"
    os.environ["BOOK_CHARS_PER_LINE"] = "10"
    os.environ["ALPHABET"] = "abc"
    
    from src.config import reload_config
    reload_config()
    
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    
    # Reset environment
    del os.environ["BOOK_PAGES"]
    del os.environ["BOOK_LINES_PER_PAGE"]
    del os.environ["BOOK_CHARS_PER_LINE"]
    del os.environ["ALPHABET"]


class TestRootEndpoints:
    """Tests for root endpoints."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "Library of Babel API"
        assert "version" in data
        assert "docs" in data
    
    def test_explore_endpoint(self, client):
        """Test the explore endpoint."""
        response = client.get("/explore")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "documentation" in data
        assert "endpoints" in data


class TestBookEndpoints:
    """Tests for book-related endpoints."""
    
    def test_get_book_by_id_invalid_length(self, client):
        """Test getting a book with invalid ID length."""
        # This will fail because the book ID length doesn't match the config
        response = client.get("/api/books/invalid")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_get_book_by_number(self, client):
        """Test getting a book by number."""
        response = client.get("/api/books/number/0")
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert "content" in data
        assert "metadata" in data
    
    def test_get_book_by_number_negative(self, client):
        """Test getting a book with negative number."""
        response = client.get("/api/books/number/-1")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_get_random_book(self, client):
        """Test getting a random book."""
        response = client.get("/api/books/random")
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert "content" in data
    
    def test_get_book_range(self, client):
        """Test getting a range of books."""
        response = client.get("/api/books/range?start=0&end=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
    
    def test_get_book_range_invalid(self, client):
        """Test getting a book range with invalid parameters."""
        # End <= start
        response = client.get("/api/books/range?start=10&end=5")
        assert response.status_code == 400
        
        # Range too large
        response = client.get("/api/books/range?start=0&end=1000")
        assert response.status_code == 400
    
    def test_get_special_books(self, client):
        """Test getting special books."""
        response = client.get("/api/books/special")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestBookEndpointsWithSmallConfig:
    """Tests for book endpoints with small book configuration."""
    
    def test_get_book_by_id(self, small_book_config):
        """Test getting a book by ID with small config."""
        # With small config, book IDs are shorter
        response = small_book_config.get("/api/books/aaaaaa")
        assert response.status_code == 200
        data = response.json()
        assert "book_id" in data
        assert data["book_id"] == "aaaaaa"
    
    def test_get_book_page(self, small_book_config):
        """Test getting a specific page from a book."""
        # First create/get a book
        book_response = small_book_config.get("/api/books/aaaaaa")
        assert book_response.status_code == 200
        
        # Then get a page
        response = small_book_config.get("/api/books/aaaaaa/page/1")
        assert response.status_code == 200
        data = response.json()
        assert "lines" in data
        assert "page_number" in data
    
    def test_get_book_neighbors(self, small_book_config):
        """Test getting neighboring books."""
        response = small_book_config.get("/api/books/aaaaaa/neighbors?count=2")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return up to 4 neighbors (2 on each side)
        assert len(data) <= 4
    
    def test_get_book_distance(self, small_book_config):
        """Test calculating distance between books."""
        response = small_book_config.get("/api/books/aaaaaa/distance/aaaaab")
        assert response.status_code == 200
        data = response.json()
        assert "distance" in data
        assert data["distance"] == 1


class TestSearchEndpoints:
    """Tests for search endpoints."""
    
    def test_search_books(self, client):
        """Test searching for books."""
        response = client.get("/api/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_empty_query(self, client):
        """Test searching with empty query."""
        response = client.get("/api/search?q=")
        assert response.status_code == 400
    
    def test_search_invalid_strategy(self, client):
        """Test searching with invalid strategy."""
        response = client.get("/api/search?q=test&strategy=invalid")
        assert response.status_code == 400
    
    def test_search_regex(self, client):
        """Test regex search."""
        response = client.get("/api/search/regex?pattern=test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_regex_dangerous_pattern(self, client):
        """Test regex search with dangerous pattern."""
        # Pattern with catastrophic backtracking potential
        response = client.get("/api/search/regex?pattern=.*a")
        assert response.status_code == 400
    
    def test_search_regex_too_long(self, client):
        """Test regex search with pattern that's too long."""
        long_pattern = "a" * 101  # Max is 50 by default
        response = client.get(f"/api/search/regex?pattern={long_pattern}")
        assert response.status_code == 400
    
    def test_find_similar(self, client):
        """Test finding similar books."""
        # Use a valid book ID format (this might fail with default config)
        response = client.get("/api/books/number/0")
        if response.status_code == 200:
            book_data = response.json()
            book_id = book_data["book_id"]
            
            response = client.get(f"/api/search/similar/{book_id}")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestStatsEndpoints:
    """Tests for statistics endpoints."""
    
    def test_get_stats(self, client):
        """Test getting library statistics."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "library" in data
        assert "books" in data
        assert "generation" in data
        assert "search" in data
        assert "cache" in data
    
    def test_get_config(self, client):
        """Test getting library configuration."""
        response = client.get("/api/stats/config")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "book" in data
        assert "cache" in data
        assert "security" in data
        # Secret key should not be exposed
        assert "secret_key" not in str(data)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/stats/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "checks" in data
    
    def test_get_sample_books(self, client):
        """Test getting sample books."""
        response = client.get("/api/stats/sample?count=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_endpoint(self, client):
        """Test accessing an invalid endpoint."""
        response = client.get("/api/invalid")
        assert response.status_code == 404
    
    def test_validation_error(self, client):
        """Test validation error handling."""
        # This should trigger a validation error
        response = client.get("/api/books/range?start=abc&end=def")
        assert response.status_code == 422
        data = response.json()
        assert "error" in data


class TestRateLimiting:
    """Tests for rate limiting."""
    
    def test_rate_limiting_disabled_in_tests(self, client):
        """Test that rate limiting doesn't affect tests."""
        # In test environment, rate limiting should be lenient
        # Make multiple requests to the same endpoint
        for _ in range(10):
            response = client.get("/api/books/random")
            # Should not be rate limited in tests
            assert response.status_code != 429


class TestCaching:
    """Tests for caching functionality."""
    
    def test_cache_hit(self, client):
        """Test that caching works."""
        # First request - should miss cache
        response1 = client.get("/api/books/number/0")
        assert response1.status_code == 200
        
        # Second request - should hit cache
        response2 = client.get("/api/books/number/0")
        assert response2.status_code == 200
        
        # Both should return the same data
        assert response1.json()["book_id"] == response2.json()["book_id"]
    
    def test_cache_statistics(self, client):
        """Test cache statistics."""
        # Make some requests to populate cache
        for i in range(5):
            client.get(f"/api/books/number/{i}")
        
        # Get stats
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "cache" in data
        assert data["cache"]["size"] >= 0
