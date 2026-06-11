"""
Data models for the Library of Babel project.

This package contains the core data structures and models used throughout
the application, including book models, encoding schemes, and library structure.
"""

from .book import Book, BookMetadata
from .encoding import Base25Encoder, BookEncoder, EncodingError
from .library import Library, LibraryConfig, LibraryStats

__all__ = [
    "Book",
    "BookConfig",
    "BookMetadata",
    "Base25Encoder",
    "BookEncoder",
    "EncodingError",
    "Library",
    "LibraryConfig",
    "LibraryStats",
]
