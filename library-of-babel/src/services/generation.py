"""
Book generation service for the Library of Babel.

This module provides the BookGenerator class which handles the generation
of books based on their identifiers or numbers.
"""

import time
from dataclasses import dataclass
from typing import Optional

from ..config import get_config
from ..models.book import Book
from ..models.encoding import BookEncoder, Base25Encoder, EncodingError


@dataclass
class GenerationStats:
    """Statistics for book generation."""
    
    total_generated: int = 0
    total_time_ms: float = 0.0
    average_time_ms: float = 0.0
    last_generation_time_ms: float = 0.0
    
    def record_generation(self, time_ms: float) -> None:
        """Record a generation operation."""
        self.total_generated += 1
        self.total_time_ms += time_ms
        self.last_generation_time_ms = time_ms
        self.average_time_ms = self.total_time_ms / self.total_generated if self.total_generated > 0 else 0


class BookGenerator:
    """
    Service for generating books in the Library of Babel.
    
    This class provides methods for generating books from various inputs:
    - Book ID (base-25 encoded string)
    - Book number (integer)
    - Random generation
    
    The generator uses the encoding scheme to convert between book identifiers
    and their content, ensuring that each book is uniquely determined by its ID.
    """
    
    def __init__(self) -> None:
        """Initialize the book generator."""
        self.config = get_config()
        self.encoder = BookEncoder()
        self.base25 = Base25Encoder()
        self.stats = GenerationStats()
    
    def generate_by_id(self, book_id: str) -> Book:
        """
        Generate a book by its ID.
        
        Args:
            book_id: The book ID (base-25 encoded string)
        
        Returns:
            The generated Book object
        
        Raises:
            EncodingError: If the book ID is invalid
        """
        start_time = time.time()
        
        try:
            # Validate the book ID
            if not self.base25.validate_book_id(book_id):
                raise EncodingError(f"Invalid book ID: {book_id}")
            
            # Generate the book
            book = self.encoder.book_id_to_book(book_id)
            
            # Record statistics
            generation_time = (time.time() - start_time) * 1000
            self.stats.record_generation(generation_time)
            
            return book
            
        except Exception as e:
            raise EncodingError(f"Failed to generate book with ID {book_id}: {e}")
    
    def generate_by_number(self, book_number: int) -> Book:
        """
        Generate a book by its number.
        
        Args:
            book_number: The book number (0 to 25^N - 1)
        
        Returns:
            The generated Book object
        
        Raises:
            EncodingError: If the book number is invalid
        """
        start_time = time.time()
        
        try:
            # Validate the book number
            if book_number < 0:
                raise EncodingError(
                    f"Book number {book_number} is out of range [0, ...)"
                )
            
            # Generate the book
            book = self.encoder.number_to_book(book_number)
            
            # Record statistics
            generation_time = (time.time() - start_time) * 1000
            self.stats.record_generation(generation_time)
            
            return book
            
        except Exception as e:
            raise EncodingError(f"Failed to generate book number {book_number}: {e}")
    
    def generate_random(self) -> Book:
        """
        Generate a random book.
        
        Returns:
            A randomly generated Book object
        """
        start_time = time.time()
        
        try:
            # Generate a random book ID
            book_id = self.base25.get_random_book_id()
            
            # Generate the book
            book = self.generate_by_id(book_id)
            
            # Record statistics
            generation_time = (time.time() - start_time) * 1000
            self.stats.record_generation(generation_time)
            
            return book
            
        except Exception as e:
            raise EncodingError(f"Failed to generate random book: {e}")
    
    def generate_range(self, start: int, end: int) -> list[Book]:
        """
        Generate a range of books.
        
        Args:
            start: Starting book number (inclusive)
            end: Ending book number (exclusive)
        
        Returns:
            List of generated Book objects
        
        Raises:
            EncodingError: If the range is invalid
        """
        if start < 0 or end <= start:
            raise EncodingError(f"Invalid range: [{start}, {end})")
        
        total_books = self.base25.get_total_books()
        if start >= total_books:
            raise EncodingError(f"Start {start} is out of range")
        
        if end > total_books:
            end = total_books
        
        books = []
        for i in range(start, end):
            books.append(self.generate_by_number(i))
        
        return books
    
    def generate_special_books(self) -> list[Book]:
        """
        Generate a collection of special/interesting books.
        
        Returns:
            List of special Book objects
        """
        special_books = []
        
        # Book 0: All 'a's (first book)
        special_books.append(self.generate_by_number(0))
        
        # Book 1: Mostly 'a's with one 'b' at the end
        special_books.append(self.generate_by_number(1))
        
        # Book with all same character (last character in alphabet)
        # Use direct ID construction to avoid astronomically large integer math.
        last_char = self.base25.alphabet[-1]
        total_chars = self.config.book.total_chars
        special_books.append(self.generate_by_id(last_char * total_chars))
        
        # A few random books
        for _ in range(5):
            special_books.append(self.generate_random())
        
        return special_books
    
    def get_generation_stats(self) -> GenerationStats:
        """
        Get generation statistics.
        
        Returns:
            GenerationStats object
        """
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset generation statistics."""
        self.stats = GenerationStats()
