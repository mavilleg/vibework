#!/usr/bin/env python3
"""
Basic test script for the Library of Babel.

This script tests the core functionality of the Library of Babel
to ensure everything is working correctly.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_encoding():
    """Test the encoding functionality."""
    print("Testing encoding...")
    
    from src.models.encoding import Base25Encoder, BookEncoder, EncodingError
    
    # Test Base25Encoder
    encoder = Base25Encoder(alphabet="abc")
    
    # Test encode/decode
    for i in range(10):
        encoded = encoder.encode(i)
        decoded = encoder.decode(encoded)
        assert decoded == i, f"Encode/decode failed for {i}"
    
    print("✓ Base25Encoder works")
    
    # Test BookEncoder
    book_encoder = BookEncoder()
    book_id = book_encoder.number_to_book_id(0)
    content = book_encoder.book_id_to_content(book_id)
    assert len(content) > 0, "Book content should not be empty"
    
    print("✓ BookEncoder works")


def test_book_generation():
    """Test book generation."""
    print("Testing book generation...")
    
    from src.services.generation import BookGenerator
    
    generator = BookGenerator()
    
    # Test generating by number
    book = generator.generate_by_number(0)
    assert book is not None, "Book generation failed"
    assert book.book_id is not None, "Book ID should not be None"
    assert book.content is not None, "Book content should not be None"
    
    print("✓ Book generation works")


def test_library():
    """Test the library functionality."""
    print("Testing library...")
    
    from src.models.library import Library
    
    library = Library()
    
    # Test getting a book
    book = library.get_book_by_number(0)
    assert book is not None, "Library book retrieval failed"
    
    # Test getting random book
    random_book = library.get_random_book()
    assert random_book is not None, "Random book generation failed"
    
    # Test getting stats
    stats = library.get_stats()
    assert stats.total_possible_books, "Total possible books should be positive"
    
    print("✓ Library works")


def test_api_imports():
    """Test that API imports work."""
    print("Testing API imports...")
    
    try:
        from src.api.books import router as books_router
        from src.api.search import router as search_router
        from src.api.stats import router as stats_router
        print("✓ API imports work")
    except Exception as e:
        print(f"✗ API import failed: {e}")
        raise


def test_config():
    """Test configuration."""
    print("Testing configuration...")
    
    from src.config import get_config
    
    config = get_config()
    assert config.name == "Library of Babel", "Config name should be 'Library of Babel'"
    assert config.book.pages > 0, "Pages should be positive"
    assert config.book.lines_per_page > 0, "Lines per page should be positive"
    assert config.book.chars_per_line > 0, "Chars per line should be positive"
    
    print("✓ Configuration works")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Library of Babel - Basic Tests")
    print("=" * 50)
    
    try:
        test_config()
        test_encoding()
        test_book_generation()
        test_library()
        test_api_imports()
        
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
