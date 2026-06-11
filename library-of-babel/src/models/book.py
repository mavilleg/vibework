"""
Book model and configuration for the Library of Babel.

This module defines the Book class which represents a single book in the library,
including its content, structure, and metadata.
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from ..config import get_config


@dataclass
class BookMetadata:
    """Metadata for a book in the Library of Babel."""
    
    book_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    generated_at: Optional[datetime] = None
    cached_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    checksum: str = ""
    
    def to_dict(self) -> dict:
        """Convert metadata to dictionary."""
        return {
            "book_id": self.book_id,
            "created_at": self.created_at.isoformat(),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "cached_at": self.cached_at.isoformat() if self.cached_at else None,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BookMetadata":
        """Create metadata from dictionary."""
        return cls(
            book_id=data["book_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            generated_at=datetime.fromisoformat(data["generated_at"]) if data["generated_at"] else None,
            cached_at=datetime.fromisoformat(data["cached_at"]) if data["cached_at"] else None,
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data["last_accessed"] else None,
            size_bytes=data.get("size_bytes", 0),
            checksum=data.get("checksum", ""),
        )


@dataclass
class Book:
    """
    Represents a book in the Library of Babel.
    
    A book is defined by its unique identifier and content. The content
    is structured according to the library's configuration (pages, lines, characters).
    
    Attributes:
        book_id: Unique identifier for the book (base-25 encoded or UUID)
        content: The full text content of the book
        pages: List of pages, each containing lines of text
        metadata: Additional information about the book
    """
    
    book_id: str
    content: str = ""
    pages: List[List[str]] = field(default_factory=list)
    metadata: BookMetadata = field(default_factory=lambda: BookMetadata(book_id=""))
    
    def __post_init__(self) -> None:
        """Initialize the book and ensure consistency."""
        if not self.metadata.book_id:
            self.metadata.book_id = self.book_id
        
        # If content is provided but pages are empty, generate pages
        if self.content and not self.pages:
            self._generate_pages_from_content()
        elif not self.content and self.pages:
            self.content = self._generate_content_from_pages()
        
        # Calculate metadata
        self._update_metadata()
    
    @classmethod
    def create_empty(cls, book_id: Optional[str] = None) -> "Book":
        """Create an empty book with the given ID or a random UUID."""
        config = get_config().book
        book_id = book_id or str(uuid4())
        
        # Generate empty content based on configuration
        total_chars = config.total_chars
        content = ""  # Empty content
        
        return cls(book_id=book_id, content=content)
    
    @classmethod
    def from_content(cls, content: str, book_id: Optional[str] = None) -> "Book":
        """Create a book from existing content."""
        book_id = book_id or cls._generate_id_from_content(content)
        return cls(book_id=book_id, content=content)
    
    @staticmethod
    def _generate_id_from_content(content: str) -> str:
        """Generate a deterministic book ID from content using hash."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _generate_pages_from_content(self) -> None:
        """Generate page structure from flat content."""
        config = get_config().book
        
        self.pages = []
        start = 0
        
        for _ in range(config.pages):
            page = []
            for _ in range(config.lines_per_page):
                end = start + config.chars_per_line
                line = self.content[start:end]
                # Pad with spaces if needed
                if len(line) < config.chars_per_line:
                    line = line.ljust(config.chars_per_line)
                page.append(line)
                start = end
            self.pages.append(page)
    
    def _generate_content_from_pages(self) -> str:
        """Generate flat content from page structure."""
        return "".join("".join(line for line in page) for page in self.pages)
    
    def _update_metadata(self) -> None:
        """Update book metadata."""
        self.metadata.size_bytes = len(self.content.encode('utf-8'))
        self.metadata.checksum = hashlib.sha256(self.content.encode('utf-8')).hexdigest()
        if not self.metadata.generated_at:
            self.metadata.generated_at = datetime.utcnow()
    
    def get_page(self, page_num: int) -> List[str]:
        """Get a specific page by number (1-indexed)."""
        if page_num < 1 or page_num > len(self.pages):
            raise IndexError(f"Page number must be between 1 and {len(self.pages)}")
        return self.pages[page_num - 1]
    
    def get_line(self, page_num: int, line_num: int) -> str:
        """Get a specific line by page and line number (1-indexed)."""
        page = self.get_page(page_num)
        if line_num < 1 or line_num > len(page):
            raise IndexError(f"Line number must be between 1 and {len(page)}")
        return page[line_num - 1]
    
    def get_character(self, page_num: int, line_num: int, char_num: int) -> str:
        """Get a specific character by page, line, and character number (1-indexed)."""
        line = self.get_line(page_num, line_num)
        if char_num < 1 or char_num > len(line):
            raise IndexError(f"Character number must be between 1 and {len(line)}")
        return line[char_num - 1]
    
    def contains(self, text: str) -> List[Tuple[int, int, int]]:
        """
        Check if the book contains the given text.
        
        Returns a list of (page, line, position) tuples where the text is found.
        """
        results = []
        text_len = len(text)
        if text_len == 0:
            return results
        
        for page_num, page in enumerate(self.pages, 1):
            for line_num, line in enumerate(page, 1):
                pos = 0
                while True:
                    idx = line.find(text, pos)
                    if idx == -1:
                        break
                    results.append((page_num, line_num, idx + 1))  # 1-indexed
                    pos = idx + 1
        
        return results
    
    def to_dict(self) -> dict:
        """Convert the book to a dictionary representation."""
        return {
            "book_id": self.book_id,
            "content": self.content,
            "pages": self.pages,
            "metadata": self.metadata.to_dict(),
            "stats": {
                "page_count": len(self.pages),
                "line_count": sum(len(page) for page in self.pages),
                "char_count": len(self.content),
            }
        }
    
    def to_json(self) -> str:
        """Convert the book to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Book":
        """Create a book from a dictionary."""
        metadata = BookMetadata.from_dict(data.get("metadata", {}))
        return cls(
            book_id=data["book_id"],
            content=data.get("content", ""),
            pages=data.get("pages", []),
            metadata=metadata,
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Book":
        """Create a book from JSON string."""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation of the book."""
        return f"Book(id={self.book_id}, pages={len(self.pages)}, chars={len(self.content)})"
    
    def __repr__(self) -> str:
        """Detailed representation of the book."""
        return f"Book(book_id='{self.book_id}', content_length={len(self.content)})"
    
    def __eq__(self, other: object) -> bool:
        """Check equality based on book ID and content."""
        if not isinstance(other, Book):
            return False
        return self.book_id == other.book_id and self.content == other.content
    
    def __hash__(self) -> int:
        """Hash based on book ID."""
        return hash(self.book_id)
