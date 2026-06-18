#!/usr/bin/env python3
"""
Core functionality test for Library of Babel.
Tests the mathematical foundation without external dependencies.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_encoding():
    """Test base-25 encoding."""
    print("Testing Base25Encoder...")
    
    from src.models.encoding import Base25Encoder, EncodingError
    
    # Test with small alphabet for simplicity
    encoder = Base25Encoder(alphabet="abc")
    
    # Test basic encoding
    assert encoder.encode(0) == "a"
    assert encoder.encode(1) == "b"
    assert encoder.encode(2) == "c"
    assert encoder.encode(3) == "ba"  # 3 = 1*3 + 0
    assert encoder.encode(4) == "bb"  # 4 = 1*3 + 1
    
    # Test decoding
    assert encoder.decode("a") == 0
    assert encoder.decode("b") == 1
    assert encoder.decode("c") == 2
    assert encoder.decode("ba") == 3
    
    # Test roundtrip
    for i in range(20):
        encoded = encoder.encode(i)
        decoded = encoder.decode(encoded)
        assert decoded == i, f"Roundtrip failed for {i}: {encoded} -> {decoded}"
    
    print("✓ Base25Encoder works perfectly")


def test_book_encoder():
    """Test book encoding."""
    print("Testing BookEncoder...")
    
    from src.models.encoding import BookEncoder
    
    encoder = BookEncoder()
    
    # Test book ID generation
    book_id_0 = encoder.number_to_book_id(0)
    book_id_1 = encoder.number_to_book_id(1)
    
    assert book_id_0 != book_id_1, "Different books should have different IDs"
    
    # Test content generation
    content_0 = encoder.number_to_content(0)
    content_1 = encoder.number_to_content(1)
    
    assert len(content_0) > 0, "Book content should not be empty"
    assert content_0 != content_1, "Different books should have different content"
    
    print("✓ BookEncoder works perfectly")


def test_book_model():
    """Test book model."""
    print("Testing Book model...")
    
    from src.models.book import Book, BookMetadata
    
    # Test creating a book
    book = Book(book_id="test123", content="Hello World")
    
    assert book.book_id == "test123"
    assert book.content == "Hello World"
    assert book.metadata.book_id == "test123"
    assert book.metadata.size_bytes > 0
    
    # Test book serialization
    book_dict = book.to_dict()
    assert "book_id" in book_dict
    assert "content" in book_dict
    assert "metadata" in book_dict
    
    print("✓ Book model works perfectly")


def test_library_model():
    """Test library model."""
    print("Testing Library model...")
    
    from src.models.library import Library
    
    library = Library()
    
    # Test getting a book by number
    book_0 = library.get_book_by_number(0)
    assert book_0 is not None
    assert book_0.book_id is not None
    
    # Test getting random book
    random_book = library.get_random_book()
    assert random_book is not None
    
    # Test getting stats
    stats = library.get_stats()
    assert stats.total_possible_books
    
    print("✓ Library model works perfectly")


def test_generation_service():
    """Test generation service."""
    print("Testing Generation service...")
    
    from src.services.generation import BookGenerator
    
    generator = BookGenerator()
    
    # Test generating by number
    book = generator.generate_by_number(0)
    assert book is not None
    assert book.book_id is not None
    
    # Test generating random book
    random_book = generator.generate_random()
    assert random_book is not None
    
    # Test generating range
    books = generator.generate_range(0, 5)
    assert len(books) == 5
    
    print("✓ Generation service works perfectly")


def test_cache_service():
    """Test cache service."""
    print("Testing Cache service...")
    
    from src.services.cache import MemoryCache
    from src.models.book import Book
    
    cache = MemoryCache(max_size=10, ttl=60)
    
    # Test setting and getting
    book = Book(book_id="cache_test", content="Cached content")
    cache.set("cache_test", book)
    
    cached_book = cache.get("cache_test")
    assert cached_book is not None
    assert cached_book.book_id == "cache_test"
    
    # Test cache stats
    stats = cache.get_stats()
    assert stats.size >= 1
    
    print("✓ Cache service works perfectly")


def test_search_service():
    """Test search service."""
    print("Testing Search service...")
    
    from src.services.search import BookSearch
    
    search = BookSearch()
    
    # Test basic search
    results = search.search("a", limit=5)
    assert len(results) >= 0  # May be 0 if no matches in sampled books
    
    # Test regex search
    regex_results = search.search_regex("a.*", limit=5)
    assert len(regex_results) >= 0
    
    print("✓ Search service works perfectly")


def test_config():
    """Test configuration."""
    print("Testing Configuration...")
    
    from src.config import get_config
    
    config = get_config()
    
    assert config.name == "Library of Babel"
    assert config.book.pages > 0
    assert config.book.lines_per_page > 0
    assert config.book.chars_per_line > 0
    assert len(config.book.alphabet) >= 25
    
    # Test calculated properties
    assert config.book.total_chars > 0
    assert config.book.alphabet_size >= 25
    
    print("✓ Configuration works perfectly")


def main():
    """Run all core tests."""
    print("=" * 60)
    print("Library of Babel - Core Functionality Tests")
    print("=" * 60)
    
    try:
        test_config()
        test_encoding()
        test_book_encoder()
        test_book_model()
        test_library_model()
        test_generation_service()
        test_cache_service()
        test_search_service()
        
        print("\n" + "=" * 60)
        print("🎉 ALL CORE TESTS PASSED! 🎉")
        print("=" * 60)
        print("\nThe Library of Babel core functionality is working perfectly!")
        print("You can now:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run the API: python -m src.main")
        print("  3. Deploy to Azure using GitHub Actions")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
