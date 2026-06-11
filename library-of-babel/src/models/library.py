"""
Library model for the Library of Babel.

This module defines the Library class which represents the entire collection
of possible books and provides methods for navigation and exploration.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .book import Book, BookMetadata
from .encoding import Base25Encoder, BookEncoder, EncodingError
from ..config import get_config


@dataclass
class LibraryStats:
    """Statistics about the library."""
    
    total_possible_books: int
    cached_books: int = 0
    storage_used_bytes: int = 0
    requests_today: int = 0
    average_generation_time_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "total_possible_books": str(self.total_possible_books),
            "cached_books": self.cached_books,
            "storage_used_bytes": self.storage_used_bytes,
            "storage_used_gb": round(self.storage_used_bytes / (1024**3), 2),
            "requests_today": self.requests_today,
            "average_generation_time_ms": round(self.average_generation_time_ms, 2),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class LibraryConfig:
    """Configuration for the library."""
    
    name: str = "The Library of Babel"
    description: str = "A digital implementation of Borges' universal library"
    version: str = "1.0.0"
    
    # Library structure
    rooms_per_hexagon: int = 6
    shelves_per_room: int = 5
    books_per_shelf: int = 32
    
    def get_total_rooms(self) -> int:
        """Calculate total number of rooms in the library."""
        config = get_config().book
        total_books = config.alphabet_size ** config.total_chars
        books_per_room = self.shelves_per_room * self.books_per_shelf
        return math.ceil(total_books / books_per_room)
    
    def get_room_coordinates(self, book_number: int) -> Tuple[int, int, int]:
        """
        Get the hexagonal coordinates for a book.
        
        Args:
            book_number: The book number
        
        Returns:
            Tuple of (hexagon_x, hexagon_y, room_index)
        """
        books_per_room = self.shelves_per_room * self.books_per_shelf
        room_number = book_number // books_per_room
        
        # Convert linear room number to hexagonal coordinates
        # Using axial coordinate system for hexagons
        hex_size = int(math.sqrt(self.rooms_per_hexagon)) + 1
        
        hex_x = room_number // (hex_size * hex_size)
        remainder = room_number % (hex_size * hex_size)
        hex_y = remainder // hex_size
        room_index = remainder % hex_size
        
        return (hex_x, hex_y, room_index)


class Library:
    """
    The Library of Babel.
    
    This class represents the entire library and provides methods for
    exploring, searching, and generating books. It implements Borges'
    concept of a universal library containing all possible books.
    
    The library is organized as an infinite (or very large) collection of
    hexagonal rooms, each containing shelves of books.
    """
    
    def __init__(self) -> None:
        """Initialize the library."""
        self.config = get_config()
        self.encoder = BookEncoder()
        self.base25 = Base25Encoder()
        self.library_config = LibraryConfig()
        
        # Initialize statistics
        self.stats = LibraryStats(
            total_possible_books=self.base25.get_total_books()
        )
        
        # Cache for frequently accessed books
        self._book_cache: Dict[str, Book] = {}
        self._access_log: List[Tuple[str, datetime]] = []
    
    def get_book_by_id(self, book_id: str) -> Book:
        """
        Get a book by its ID.
        
        Args:
            book_id: The book ID
        
        Returns:
            The Book object
        
        Raises:
            EncodingError: If the book ID is invalid
        """
        # Check cache first
        if book_id in self._book_cache:
            book = self._book_cache[book_id]
            book.metadata.access_count += 1
            book.metadata.last_accessed = datetime.utcnow()
            self._access_log.append((book_id, datetime.utcnow()))
            return book
        
        # Generate the book
        book = self.encoder.book_id_to_book(book_id)
        
        # Add to cache
        self._book_cache[book_id] = book
        book.metadata.cached_at = datetime.utcnow()
        
        # Update statistics
        self.stats.cached_books = len(self._book_cache)
        self.stats.requests_today += 1
        self._access_log.append((book_id, datetime.utcnow()))
        
        return book
    
    def get_book_by_number(self, book_number: int) -> Book:
        """
        Get a book by its number.
        
        Args:
            book_number: The book number (0 to 25^N - 1)
        
        Returns:
            The Book object
        
        Raises:
            EncodingError: If the book number is invalid
        """
        book_id = self.encoder.number_to_book_id(book_number)
        return self.get_book_by_id(book_id)
    
    def get_random_book(self) -> Book:
        """
        Get a random book from the library.
        
        Returns:
            A random Book object
        """
        book_id = self.base25.get_random_book_id()
        return self.get_book_by_id(book_id)
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[Book, List[Tuple[int, int, int]]]]:
        """
        Search for books containing the query text.
        
        This is a brute-force search that checks books sequentially.
        For large libraries, this is impractical, so it's limited to
        a reasonable number of books.
        
        Args:
            query: The text to search for
            limit: Maximum number of results to return
        
        Returns:
            List of (book, matches) tuples where matches are (page, line, position)
        """
        results = []
        
        if not query or len(query) == 0:
            return results
        
        # For demonstration, search a limited number of books
        max_books_to_search = 10000
        
        for i in range(max_books_to_search):
            if len(results) >= limit:
                break
            
            book = self.get_book_by_number(i)
            matches = book.contains(query)
            
            if matches:
                results.append((book, matches))
        
        return results
    
    def get_neighbors(self, book_id: str, count: int = 5) -> List[Book]:
        """
        Get neighboring books for a given book ID.
        
        Args:
            book_id: The central book ID
            count: Number of neighbors to return on each side
        
        Returns:
            List of neighboring Book objects
        """
        neighbor_ids = self.encoder.get_neighboring_books(book_id, count)
        return [self.get_book_by_id(bid) for bid in neighbor_ids]
    
    def get_distance(self, book_id1: str, book_id2: str) -> int:
        """
        Calculate the distance between two books.
        
        Args:
            book_id1: First book ID
            book_id2: Second book ID
        
        Returns:
            The distance (number of books between them)
        """
        return self.encoder.get_distance(book_id1, book_id2)
    
    def get_room_coordinates(self, book_id: str) -> Tuple[int, int, int]:
        """
        Get the hexagonal room coordinates for a book.
        
        Args:
            book_id: The book ID
        
        Returns:
            Tuple of (hexagon_x, hexagon_y, room_index)
        """
        try:
            book_number = self.encoder.book_id_to_number(book_id)
            return self.library_config.get_room_coordinates(book_number)
        except EncodingError:
            return (0, 0, 0)
    
    def get_stats(self) -> LibraryStats:
        """
        Get current library statistics.
        
        Returns:
            LibraryStats object
        """
        # Calculate storage used
        storage_used = sum(
            len(book.content.encode('utf-8')) 
            for book in self._book_cache.values()
        )
        self.stats.storage_used_bytes = storage_used
        self.stats.last_updated = datetime.utcnow()
        
        return self.stats
    
    def clear_cache(self) -> None:
        """Clear the book cache."""
        self._book_cache.clear()
        self.stats.cached_books = 0
        self.stats.storage_used_bytes = 0
    
    def get_recently_accessed(self, limit: int = 10) -> List[Book]:
        """
        Get recently accessed books.
        
        Args:
            limit: Maximum number of books to return
        
        Returns:
            List of recently accessed Book objects
        """
        # Get unique book IDs from access log
        recent_ids = []
        for book_id, timestamp in reversed(self._access_log):
            if book_id not in recent_ids:
                recent_ids.append(book_id)
                if len(recent_ids) >= limit:
                    break
        
        return [self.get_book_by_id(bid) for bid in recent_ids]
    
    def generate_sample_books(self, count: int = 10) -> List[Book]:
        """
        Generate sample books for demonstration.
        
        Args:
            count: Number of sample books to generate
        
        Returns:
            List of sample Book objects
        """
        samples = []
        
        # Include some special books
        special_books = [
            # Book 0 (all 'a's)
            self.get_book_by_number(0),
            # Book 1 (mostly 'a's with one 'b')
            self.get_book_by_number(1),
            # A random book
            self.get_random_book(),
        ]
        
        for i in range(count):
            if i < len(special_books):
                samples.append(special_books[i])
            else:
                samples.append(self.get_random_book())
        
        return samples
    
    def find_meaningful_books(self, limit: int = 100) -> List[Book]:
        """
        Attempt to find books with meaningful content.
        
        This is a heuristic search that looks for books with patterns
        that might resemble meaningful text (repeated spaces, common
        letter combinations, etc.).
        
        Args:
            limit: Maximum number of books to search
        
        Returns:
            List of potentially meaningful Book objects
        """
        meaningful = []
        
        for i in range(limit):
            book = self.get_book_by_number(i)
            
            # Simple heuristics for meaningful content
            content = book.content
            
            # Check for word-like patterns (spaces between letters)
            space_count = content.count(' ')
            if space_count > 100:  # More than 100 spaces
                # Check for reasonable word lengths
                words = content.split()
                avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
                
                if 3 < avg_word_length < 10:  # Average word length between 3 and 10
                    meaningful.append(book)
            
            # Check for repeated patterns
            if len(set(content)) < 10:  # Less than 10 unique characters
                meaningful.append(book)
        
        return meaningful
    
    def __str__(self) -> str:
        """String representation of the library."""
        return (
            f"Library of Babel("
            f"total_books={self.stats.total_possible_books}, "
            f"cached={self.stats.cached_books})"
        )
    
    def __repr__(self) -> str:
        """Detailed representation of the library."""
        return (
            f"Library(name='{self.library_config.name}', "
            f"version='{self.library_config.version}', "
            f"total_books={self.stats.total_possible_books})"
        )
