#!/usr/bin/env python3
"""
Library of Babel - Interactive Demo

This script demonstrates the core functionality of the Library of Babel
without requiring any external dependencies.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.library import Library
from src.models.encoding import Base25Encoder, BookEncoder
from src.services.generation import BookGenerator
from src.config import get_config


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_encoding():
    """Demonstrate the base-25 encoding."""
    print_header("BASE-25 ENCODING DEMO")
    
    encoder = Base25Encoder(alphabet="abcdefghijklmnopqrstuvwxyz ,.")
    
    print(f"Alphabet: {encoder.alphabet}")
    print(f"Base: {encoder.base}")
    
    # Show some encoding examples
    numbers = [0, 1, 2, 24, 25, 100, 1000]
    print("\nEncoding examples:")
    for num in numbers:
        encoded = encoder.encode(num)
        decoded = encoder.decode(encoded)
        print(f"  {num:4d} -> '{encoded}' -> {decoded}")
    
    # Show the scale
    config = get_config()
    total_chars = config.book.total_chars
    total_books = encoder.get_total_books()
    
    print(f"\nBook configuration:")
    print(f"  Pages: {config.book.pages}")
    print(f"  Lines per page: {config.book.lines_per_page}")
    print(f"  Characters per line: {config.book.chars_per_line}")
    print(f"  Total characters per book: {total_chars:,}")
    print(f"  Total possible books: 25^{total_chars:,} ≈ 10^{int(total_chars * 0.92):,}")


def demo_books():
    """Demonstrate book generation."""
    print_header("BOOK GENERATION DEMO")
    
    generator = BookGenerator()
    
    # Generate first few books
    print("First 5 books:")
    for i in range(5):
        book = generator.generate_by_number(i)
        # Show first 50 characters of content
        preview = book.content[:50] + "..." if len(book.content) > 50 else book.content
        print(f"  Book {i}: {preview}")
    
    # Generate a random book
    print("\nRandom book:")
    random_book = generator.generate_random()
    print(f"  ID: {random_book.book_id[:20]}...")
    print(f"  Content preview: {random_book.content[:50]}...")
    print(f"  Size: {len(random_book.content):,} characters")


def demo_library():
    """Demonstrate library functionality."""
    print_header("LIBRARY DEMO")
    
    library = Library()
    
    # Get library statistics
    stats = library.get_stats()
    print(f"Library Statistics:")
    # Use scientific notation for the huge number
    total_books = stats.total_possible_books
    if total_books > 10**100:
        import math
        log10 = math.log10(total_books)
        print(f"  Total possible books: 10^{log10:.0f} (25^1,312,000)")
    else:
        print(f"  Total possible books: {total_books}")
    print(f"  Cached books: {stats.cached_books}")
    
    # Get a specific book
    print(f"\nGetting book #0:")
    book_0 = library.get_book_by_number(0)
    print(f"  ID: {book_0.book_id[:20]}...")
    print(f"  Content: {book_0.content[:60]}...")
    
    # Get neighbors
    print(f"\nGetting neighbors of book #100:")
    book_100 = library.get_book_by_number(100)
    neighbors = library.get_neighbors(book_100.book_id, count=2)
    for i, neighbor in enumerate(neighbors):
        distance = library.get_distance(book_100.book_id, neighbor.book_id)
        print(f"  Neighbor {i+1}: distance={distance}, preview={neighbor.content[:30]}...")


def demo_search():
    """Demonstrate search functionality."""
    print_header("SEARCH DEMO")
    
    from src.services.search import BookSearch
    
    search = BookSearch()
    
    # Search for books containing "abc"
    print("Searching for books containing 'abc'...")
    results = search.search("abc", limit=3, strategy="sequential")
    
    if results:
        for i, result in enumerate(results):
            print(f"  Result {i+1}:")
            print(f"    Book ID: {result.book.book_id[:16]}...")
            print(f"    Matches: {len(result.matches)}")
            print(f"    Score: {result.score:.2f}")
    else:
        print("  No results found in sampled books")
    
    # Search for similar books
    print(f"\nFinding books similar to book #0:")
    similar = search.find_similar("a" * 40, limit=3)  # Short ID for demo
    for i, result in enumerate(similar):
        print(f"  Similar {i+1}: similarity={result.score:.4f}")


def demo_mathematics():
    """Demonstrate the mathematical foundation."""
    print_header("MATHEMATICAL FOUNDATION")
    
    encoder = BookEncoder()
    config = get_config()
    
    # Show the relationship between book numbers and IDs
    print("Book Number to ID Mapping:")
    for num in [0, 1, 25, 100, 1000]:
        book_id = encoder.number_to_book_id(num)
        content = encoder.book_id_to_content(book_id)
        print(f"  {num:4d} -> {book_id[:10]}... -> {content[:10]}...")
    
    # Calculate some interesting statistics
    total_chars = config.book.total_chars
    import math
    log10_total = total_chars * math.log10(25)
    
    print(f"\nScale Comparison:")
    print(f"  Atoms in observable universe: ~10^80")
    print(f"  Total possible books: ~10^{log10_total:.0f}")
    print(f"  That's 10^{log10_total - 80:.0f} times more books than atoms in the universe!")
    
    # Show the first few characters of book 0
    book_0_content = encoder.number_to_content(0)
    print(f"\nBook 0 content (first 40 chars):")
    print(f"  '{book_0_content[:40]}'")


def main():
    """Run the interactive demo."""
    print("\n" + "📚" * 30)
    print("  LIBRARY OF BABEL - INTERACTIVE DEMO")
    print("  A digital implementation of Borges' universal library")
    print("📚" * 30)
    
    try:
        demo_encoding()
        demo_books()
        demo_library()
        demo_search()
        demo_mathematics()
        
        print_header("DEMO COMPLETE")
        print("\n🎉 The Library of Babel is working perfectly!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run the API: python -m src.main")
        print("  3. Visit http://localhost:8000/docs for interactive API docs")
        print("  4. Deploy to Azure using GitHub Actions")
        print("\nThe library contains all possible books of 410 pages × 40 lines × 80 characters.")
        config = get_config()
        print(f"Total possible books: 25^{config.book.total_chars:,} ≈ 10^{int(config.book.total_chars * 0.92):,}")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
