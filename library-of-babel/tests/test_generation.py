"""
Tests for the book generation service.

This module tests the BookGenerator class.
"""

import pytest
from src.services.generation import BookGenerator, GenerationStats
from src.models.encoding import EncodingError


class TestBookGenerator:
    """Tests for BookGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = BookGenerator()
    
    def test_generate_by_id(self):
        """Test generating a book by ID."""
        # Generate using a valid book ID derived from book number 0
        valid_book_id = self.generator.encoder.number_to_book_id(0)
        book = self.generator.generate_by_id(valid_book_id)
        assert book is not None
        assert book.book_id is not None
        assert book.content is not None
    
    def test_generate_by_number(self):
        """Test generating a book by number."""
        book = self.generator.generate_by_number(0)
        assert book is not None
        assert book.book_id is not None
        assert book.content is not None
    
    def test_generate_random(self):
        """Test generating a random book."""
        book = self.generator.generate_random()
        assert book is not None
        assert book.book_id is not None
        assert book.content is not None
    
    def test_generate_range(self):
        """Test generating a range of books."""
        books = self.generator.generate_range(0, 5)
        assert len(books) == 5
        assert all(book is not None for book in books)
    
    def test_generate_special_books(self):
        """Test generating special books."""
        books = self.generator.generate_special_books()
        assert len(books) > 0
        assert all(book is not None for book in books)
    
    def test_invalid_book_id_raises(self):
        """Test that invalid book IDs raise errors."""
        with pytest.raises(EncodingError):
            self.generator.generate_by_id("invalid")
    
    def test_invalid_book_number_raises(self):
        """Test that invalid book numbers raise errors."""
        with pytest.raises(EncodingError):
            self.generator.generate_by_number(-1)
    
    def test_invalid_range_raises(self):
        """Test that invalid ranges raise errors."""
        with pytest.raises(EncodingError):
            self.generator.generate_range(10, 5)
    
    def test_generation_stats(self):
        """Test generation statistics."""
        initial_stats = self.generator.get_generation_stats()
        assert isinstance(initial_stats, GenerationStats)
        
        # Generate some books
        self.generator.generate_by_number(0)
        self.generator.generate_by_number(1)
        
        updated_stats = self.generator.get_generation_stats()
        assert updated_stats.total_generated >= 2
    
    def test_reset_stats(self):
        """Test resetting statistics."""
        self.generator.generate_by_number(0)
        self.generator.reset_stats()
        
        stats = self.generator.get_generation_stats()
        assert stats.total_generated == 0


class TestGenerationStats:
    """Tests for GenerationStats."""
    
    def test_initial_stats(self):
        """Test initial statistics values."""
        stats = GenerationStats()
        assert stats.total_generated == 0
        assert stats.total_time_ms == 0.0
        assert stats.average_time_ms == 0.0
    
    def test_record_generation(self):
        """Test recording generation operations."""
        stats = GenerationStats()
        stats.record_generation(10.0)
        
        assert stats.total_generated == 1
        assert stats.total_time_ms == 10.0
        assert stats.last_generation_time_ms == 10.0
        assert stats.average_time_ms == 10.0
        
        stats.record_generation(20.0)
        assert stats.total_generated == 2
        assert stats.total_time_ms == 30.0
        assert stats.average_time_ms == 15.0
