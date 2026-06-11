"""
Search service for the Library of Babel.

This module provides search functionality for finding books that contain
specific text or patterns. Given the enormous size of the library,
search is inherently limited and uses various strategies to find
interesting results.
"""

import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..config import get_config
from ..models.book import Book
from ..models.encoding import BookEncoder, Base25Encoder
from .generation import BookGenerator


@dataclass
class SearchResult:
    """A single search result."""
    
    book: Book
    matches: List[Tuple[int, int, int]]  # (page, line, position)
    score: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "book_id": self.book.book_id,
            "matches": [
                {"page": p, "line": l, "position": pos} 
                for p, l, pos in self.matches
            ],
            "score": self.score,
            "book": self.book.to_dict(),
        }


@dataclass
class SearchStats:
    """Statistics for search operations."""
    
    total_searches: int = 0
    total_books_searched: int = 0
    total_matches: int = 0
    average_search_time_ms: float = 0.0
    last_search_time_ms: float = 0.0
    
    def record_search(self, books_searched: int, matches: int, time_ms: float) -> None:
        """Record a search operation."""
        self.total_searches += 1
        self.total_books_searched += books_searched
        self.total_matches += matches
        self.last_search_time_ms = time_ms
        self.average_search_time_ms = (
            self.total_books_searched / self.total_searches 
            if self.total_searches > 0 else 0
        )


class BookSearch:
    """
    Service for searching books in the Library of Babel.
    
    This class provides various search strategies for finding books that
    contain specific text or patterns. Due to the enormous size of the
    library, exhaustive search is impossible, so this service uses
    heuristic and sampling-based approaches.
    """
    
    def __init__(self) -> None:
        """Initialize the search service."""
        self.config = get_config()
        self.encoder = BookEncoder()
        self.base25 = Base25Encoder()
        self.generator = BookGenerator()
        self.stats = SearchStats()
    
    def search(self, query: str, limit: int = 10, 
               strategy: str = "sequential") -> List[SearchResult]:
        """
        Search for books containing the query text.
        
        Args:
            query: The text to search for
            limit: Maximum number of results to return
            strategy: Search strategy to use (sequential, random, smart)
        
        Returns:
            List of SearchResult objects
        """
        start_time = time.time()
        
        if not query or len(query) == 0:
            return []
        
        query = query.lower()
        
        if strategy == "sequential":
            results = self._search_sequential(query, limit)
        elif strategy == "random":
            results = self._search_random(query, limit)
        elif strategy == "smart":
            results = self._search_smart(query, limit)
        else:
            results = self._search_sequential(query, limit)
        
        # Record statistics
        search_time = (time.time() - start_time) * 1000
        books_searched = min(10000, limit * 100)  # Approximate
        matches = sum(len(r.matches) for r in results)
        self.stats.record_search(books_searched, matches, search_time)
        
        return results
    
    def _search_sequential(self, query: str, limit: int) -> List[SearchResult]:
        """
        Sequential search from book 0 upwards.
        
        This is the simplest search strategy, checking books in order.
        It's deterministic but may not find the most interesting results.
        """
        results = []
        max_books = 10000  # Limit for performance
        
        for i in range(max_books):
            if len(results) >= limit:
                break
            
            book = self.generator.generate_by_number(i)
            matches = book.contains(query)
            
            if matches:
                # Calculate a simple score based on number of matches
                score = len(matches) / len(query)
                results.append(SearchResult(book=book, matches=matches, score=score))
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]
    
    def _search_random(self, query: str, limit: int) -> List[SearchResult]:
        """
        Random sampling search.
        
        This strategy randomly samples books from the library.
        It's non-deterministic but may find interesting results faster.
        """
        results = []
        max_samples = 1000  # Number of random books to check
        
        for _ in range(max_samples):
            if len(results) >= limit:
                break
            
            book = self.generator.generate_random()
            matches = book.contains(query)
            
            if matches:
                score = len(matches) / len(query)
                results.append(SearchResult(book=book, matches=matches, score=score))
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]
    
    def _search_smart(self, query: str, limit: int) -> List[SearchResult]:
        """
        Smart search using heuristics.
        
        This strategy uses various heuristics to find potentially
        interesting books that contain the query.
        """
        results = []
        
        # First, try sequential search for early books (more likely to have patterns)
        early_results = self._search_sequential(query, limit // 2)
        results.extend(early_results)
        
        # Then, try some special books
        special_books = self.generator.generate_special_books()
        for book in special_books:
            if len(results) >= limit:
                break
            
            matches = book.contains(query)
            if matches:
                score = len(matches) / len(query) * 2  # Boost score for special books
                results.append(SearchResult(book=book, matches=matches, score=score))
        
        # Finally, try some random books
        random_results = self._search_random(query, limit // 2)
        results.extend(random_results)
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]
    
    def search_regex(self, pattern: str, limit: int = 10) -> List[SearchResult]:
        """
        Search for books matching a regular expression.
        
        Args:
            pattern: The regex pattern to search for
            limit: Maximum number of results to return
        
        Returns:
            List of SearchResult objects
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []
        
        results = []
        max_books = 1000  # Limit for performance
        
        for i in range(max_books):
            if len(results) >= limit:
                break
            
            book = self.generator.generate_by_number(i)
            
            # Search each page and line
            matches = []
            for page_num, page in enumerate(book.pages, 1):
                for line_num, line in enumerate(page, 1):
                    for match in compiled.finditer(line):
                        matches.append((page_num, line_num, match.start() + 1))
            
            if matches:
                score = len(matches)
                results.append(SearchResult(book=book, matches=matches, score=score))
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]
    
    def find_similar(self, book_id: str, limit: int = 10) -> List[SearchResult]:
        """
        Find books similar to the given book.
        
        This searches for books that have similar content patterns
        to the given book.
        
        Args:
            book_id: The book ID to find similar books for
            limit: Maximum number of results to return
        
        Returns:
            List of SearchResult objects
        """
        try:
            book = self.generator.generate_by_id(book_id)
        except Exception:
            return []
        
        # Get the first few characters as a pattern
        pattern_length = min(10, len(book.content))
        pattern = book.content[:pattern_length]
        
        # Search for books that start with the same pattern
        results = []
        max_books = 1000
        
        for i in range(max_books):
            if len(results) >= limit:
                break
            
            test_book = self.generator.generate_by_number(i)
            
            if test_book.content.startswith(pattern):
                # Calculate similarity score
                similarity = self._calculate_similarity(book.content, test_book.content)
                results.append(SearchResult(
                    book=test_book, 
                    matches=[],  # No specific matches, just similarity
                    score=similarity
                ))
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]
    
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two book contents.
        
        This is a simple implementation that compares character-by-character.
        
        Args:
            content1: First book content
            content2: Second book content
        
        Returns:
            Similarity score between 0 and 1
        """
        if len(content1) != len(content2):
            return 0.0
        
        matches = sum(1 for c1, c2 in zip(content1, content2) if c1 == c2)
        return matches / len(content1)
    
    def get_stats(self) -> SearchStats:
        """
        Get search statistics.
        
        Returns:
            SearchStats object
        """
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset search statistics."""
        self.stats = SearchStats()
