"""
Library of Babel - A digital implementation of Borges' universal library.

This project provides a system to explore the mathematical concept of a library
containing all possible books of a given format.

Key Statistics:
- Total Possible Books: 25^1,312,000 ≈ 10^1,834,100
- Book Format: 410 pages × 40 lines × ~80 characters
- Character Set: 25 characters (22 letters + space + comma + period)

Author: Library of Babel Project
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Library of Babel Project"
__description__ = "Digital implementation of Borges' Library of Babel"
__url__ = "https://github.com/mavilleg/vibework/tree/main/library-of-babel"

# Import key modules for easy access
from .models.book import Book, BookMetadata
from .models.encoding import Base25Encoder, BookEncoder
from .models.library import Library, LibraryConfig, LibraryStats
from .services.generation import BookGenerator
from .services.cache import BookCache
from .services.search import BookSearch

__all__ = [
    "__version__",
    "__author__",
    "__description__",
    "__url__",
    "Book",
    "BookMetadata",
    "Base25Encoder",
    "BookEncoder",
    "Library",
    "LibraryConfig",
    "LibraryStats",
    "BookGenerator",
    "BookCache",
    "BookSearch",
]
