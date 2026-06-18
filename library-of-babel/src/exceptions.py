"""
Custom exceptions for the Library of Babel project.

This module provides a hierarchy of custom exceptions for better error handling
and consistent error responses throughout the application.
"""

from typing import Optional, Dict, Any


class LibraryOfBabelError(Exception):
    """Base exception for Library of Babel errors."""
    
    def __init__(self, message: str, code: str = "ERROR", 
                 status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        result = {
            "error": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class BookNotFoundError(LibraryOfBabelError):
    """Raised when a book is not found."""
    
    def __init__(self, book_id: str):
        super().__init__(
            message=f"Book not found: {book_id}",
            code="BOOK_NOT_FOUND",
            status_code=404,
            details={"book_id": book_id}
        )


class InvalidBookIdError(LibraryOfBabelError):
    """Raised when a book ID is invalid."""
    
    def __init__(self, book_id: str, reason: str = ""):
        message = f"Invalid book ID: {book_id}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="INVALID_BOOK_ID",
            status_code=400,
            details={"book_id": book_id, "reason": reason}
        )


class InvalidBookNumberError(LibraryOfBabelError):
    """Raised when a book number is invalid."""
    
    def __init__(self, book_number: int, reason: str = ""):
        message = f"Invalid book number: {book_number}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="INVALID_BOOK_NUMBER",
            status_code=400,
            details={"book_number": book_number, "reason": reason}
        )


class RateLimitExceededError(LibraryOfBabelError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after


class InvalidSearchQueryError(LibraryOfBabelError):
    """Raised when a search query is invalid."""
    
    def __init__(self, query: str, reason: str = ""):
        message = f"Invalid search query: {query}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="INVALID_SEARCH_QUERY",
            status_code=400,
            details={"query": query, "reason": reason}
        )


class RegexError(LibraryOfBabelError):
    """Raised when there's an error with regular expression."""
    
    def __init__(self, pattern: str, reason: str = ""):
        message = f"Invalid regular expression pattern: {pattern}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="INVALID_REGEX",
            status_code=400,
            details={"pattern": pattern, "reason": reason}
        )


class AuthenticationError(LibraryOfBabelError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=401
        )


class AuthorizationError(LibraryOfBabelError):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Authorization failed"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_FAILED",
            status_code=403
        )


class ConfigurationError(LibraryOfBabelError):
    """Raised when there's a configuration error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class CacheError(LibraryOfBabelError):
    """Raised when there's a cache-related error."""
    
    def __init__(self, message: str, cache_type: str = "unknown"):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            status_code=500,
            details={"cache_type": cache_type}
        )


class GenerationError(LibraryOfBabelError):
    """Raised when book generation fails."""
    
    def __init__(self, message: str, book_id: Optional[str] = None):
        details = {}
        if book_id:
            details["book_id"] = book_id
        super().__init__(
            message=message,
            code="GENERATION_ERROR",
            status_code=500,
            details=details
        )
