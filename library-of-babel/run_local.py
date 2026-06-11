#!/usr/bin/env python3
"""
Library of Babel - Local Server

A standalone version that runs the core Library of Babel functionality
without requiring external dependencies like FastAPI.

This provides a simple HTTP server using only Python's built-in modules.
"""

import sys
import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.library import Library
from src.models.encoding import BookEncoder, Base25Encoder
from src.services.generation import BookGenerator
from src.services.search import BookSearch
from src.config import get_config


class LibraryOfBabelHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Library of Babel API."""
    
    # Initialize services (shared across all requests)
    library = Library()
    generator = BookGenerator()
    search_service = BookSearch()
    encoder = BookEncoder()
    
    def _set_headers(self, status_code=200, content_type="application/json"):
        """Set response headers."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def _send_json(self, data, status_code=200):
        """Send JSON response."""
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def _send_error(self, message, status_code=400):
        """Send error response."""
        self._send_json({"error": message}, status_code)
    
    def _parse_path(self):
        """Parse the request path and query parameters."""
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)
        return path, query_params
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            path, query_params = self._parse_path()
            
            # Root endpoint
            if path == "/" or path == "/index.html":
                self._handle_root()
            
            # API endpoints
            elif path.startswith("/api/books/"):
                self._handle_books(path, query_params)
            elif path.startswith("/api/search/"):
                self._handle_search(path, query_params)
            elif path.startswith("/api/stats/"):
                self._handle_stats(path, query_params)
            elif path == "/api/books":
                self._handle_books_list(query_params)
            elif path == "/api/search":
                self._handle_search_list(query_params)
            elif path == "/api/stats":
                self._handle_stats_list()
            
            # Static files
            elif path.startswith("/static/"):
                self._handle_static(path)
            
            # 404
            else:
                self._send_error("Not found", 404)
                
        except Exception as e:
            self._send_error(f"Internal server error: {str(e)}", 500)
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self._set_headers(200)
    
    def _handle_root(self):
        """Handle root endpoint."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Library of Babel API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { background: #0078D4; color: white; padding: 3px 8px; border-radius: 3px; font-family: monospace; }
                code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }
                .stats { background: #e8f5e8; padding: 15px; margin: 20px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>📚 Library of Babel API</h1>
            <p>A digital implementation of Jorge Luis Borges' Library of Babel.</p>
            
            <div class="stats">
                <h2>📊 Library Statistics</h2>
                <p><strong>Total Possible Books:</strong> 25^1,312,000 ≈ 10^1,834,097</p>
                <p><strong>Book Format:</strong> 410 pages × 40 lines × 80 characters</p>
                <p><strong>Alphabet:</strong> abcdefghijklmnopqrstuvwxyz ,.</p>
            </div>
            
            <h2>🔌 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/books/{book_id}</code>
                <p>Get a specific book by its ID</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/books/number/{book_number}</code>
                <p>Get a book by its number</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/books/random</code>
                <p>Get a random book from the library</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/books/range?start=0&end=10</code>
                <p>Get a range of books</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/books/special</code>
                <p>Get special/interesting books</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/search?q=text</code>
                <p>Search for books containing text</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/stats</code>
                <p>Get library statistics</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/stats/health</code>
                <p>Health check endpoint</p>
            </div>
            
            <h2>📖 Examples</h2>
            <p>Try these URLs:</p>
            <ul>
                <li><a href="/api/books/random">/api/books/random</a> - Random book</li>
                <li><a href="/api/books/number/0">/api/books/number/0</a> - Book 0 (all 'a's)</li>
                <li><a href="/api/books/number/1">/api/books/number/1</a> - Book 1</li>
                <li><a href="/api/stats">/api/stats</a> - Library statistics</li>
                <li><a href="/api/search?q=abc">/api/search?q=abc</a> - Search for 'abc'</li>
            </ul>
            
            <h2>🔗 Links</h2>
            <p><a href="https://github.com/mavilleg/vibework/tree/main/library-of-babel">GitHub Repository</a></p>
        </body>
        </html>
        """
        self._set_headers(200, "text/html")
        self.wfile.write(html.encode('utf-8'))
    
    def _handle_books(self, path, query_params):
        """Handle /api/books/* endpoints."""
        parts = path.split('/')
        
        # /api/books/{book_id}
        if len(parts) == 4 and parts[3]:
            book_id = parts[3]
            try:
                book = self.library.get_book_by_id(book_id)
                self._send_json(book.to_dict())
            except Exception as e:
                self._send_error(f"Invalid book ID: {str(e)}", 400)
        
        # /api/books/number/{book_number}
        elif len(parts) == 5 and parts[3] == "number":
            try:
                book_number = int(parts[4])
                book = self.generator.generate_by_number(book_number)
                self._send_json(book.to_dict())
            except ValueError:
                self._send_error("Invalid book number", 400)
            except Exception as e:
                self._send_error(f"Failed to generate book: {str(e)}", 500)
        
        # /api/books/random
        elif len(parts) == 4 and parts[3] == "random":
            book = self.generator.generate_random()
            self._send_json(book.to_dict())
        
        # /api/books/range
        elif len(parts) == 4 and parts[3] == "range":
            start = int(query_params.get('start', [0])[0])
            end = int(query_params.get('end', [10])[0])
            books = self.generator.generate_range(start, end)
            self._send_json([book.to_dict() for book in books])
        
        # /api/books/special
        elif len(parts) == 4 and parts[3] == "special":
            books = self.generator.generate_special_books()
            self._send_json([book.to_dict() for book in books])
        
        else:
            self._send_error("Invalid books endpoint", 404)
    
    def _handle_books_list(self, query_params):
        """Handle /api/books endpoint."""
        # Default: get first 10 books
        books = self.generator.generate_range(0, 10)
        self._send_json([book.to_dict() for book in books])
    
    def _handle_search(self, path, query_params):
        """Handle /api/search/* endpoints."""
        parts = path.split('/')
        
        # /api/search?q=query
        if len(parts) == 3:
            query = query_params.get('q', [''])[0]
            limit = int(query_params.get('limit', [10])[0])
            strategy = query_params.get('strategy', ['sequential'])[0]
            
            if not query:
                self._send_error("Search query is required", 400)
                return
            
            results = self.search_service.search(query, limit=limit, strategy=strategy)
            output = []
            for result in results:
                output.append({
                    "book_id": result.book.book_id,
                    "matches": [{"page": p, "line": l, "position": pos} for p, l, pos in result.matches],
                    "score": result.score,
                    "book": result.book.to_dict()
                })
            self._send_json(output)
        
        # /api/search/regex
        elif len(parts) == 4 and parts[3] == "regex":
            pattern = query_params.get('pattern', [''])[0]
            limit = int(query_params.get('limit', [10])[0])
            
            if not pattern:
                self._send_error("Pattern is required", 400)
                return
            
            results = self.search_service.search_regex(pattern, limit=limit)
            output = []
            for result in results:
                output.append({
                    "book_id": result.book.book_id,
                    "matches": [{"page": p, "line": l, "position": pos} for p, l, pos in result.matches],
                    "score": result.score,
                    "book": result.book.to_dict()
                })
            self._send_json(output)
        
        else:
            self._send_error("Invalid search endpoint", 404)
    
    def _handle_search_list(self, query_params):
        """Handle /api/search endpoint."""
        self._handle_search("/api/search", query_params)
    
    def _handle_stats(self, path, query_params):
        """Handle /api/stats/* endpoints."""
        parts = path.split('/')
        
        # /api/stats
        if len(parts) == 3:
            self._handle_stats_list()
        
        # /api/stats/health
        elif len(parts) == 4 and parts[3] == "health":
            self._send_json({
                "status": "healthy",
                "version": get_config().version,
                "environment": get_config().environment,
                "timestamp": self.library.get_book_by_number(0).metadata.generated_at.isoformat()
            })
        
        # /api/stats/config
        elif len(parts) == 4 and parts[3] == "config":
            config = get_config()
            self._send_json({
                "app": {
                    "name": config.name,
                    "version": config.version,
                    "debug": config.debug,
                    "environment": config.environment,
                },
                "book": {
                    "pages": config.book.pages,
                    "lines_per_page": config.book.lines_per_page,
                    "chars_per_line": config.book.chars_per_line,
                    "alphabet": config.book.alphabet,
                    "total_chars": config.book.total_chars,
                }
            })
        
        else:
            self._send_error("Invalid stats endpoint", 404)
    
    def _handle_stats_list(self):
        """Handle /api/stats endpoint."""
        import math
        config = get_config()
        
        # Get library stats
        stats = self.library.get_stats()
        
        # Calculate log10 for huge numbers
        log10_total = config.book.total_chars * math.log10(25)
        
        self._send_json({
            "library": {
                "name": "Library of Babel",
                "version": config.version,
                "environment": config.environment,
            },
            "books": {
                "total_possible": f"10^{log10_total:.0f} (25^{config.book.total_chars:,})",
                "cached": stats.cached_books,
                "storage_used_bytes": stats.storage_used_bytes,
            },
            "generation": {
                "total_generated": self.generator.stats.total_generated,
                "average_time_ms": round(self.generator.stats.average_time_ms, 2),
            },
            "search": {
                "total_searches": self.search_service.stats.total_searches,
                "total_matches": self.search_service.stats.total_matches,
            },
            "config": {
                "pages": config.book.pages,
                "lines_per_page": config.book.lines_per_page,
                "chars_per_line": config.book.chars_per_line,
                "total_chars_per_book": config.book.total_chars,
            }
        })
    
    def _handle_static(self, path):
        """Handle static files."""
        # For now, just return 404 for static files
        self._send_error("Not found", 404)


def run_server(port=8000):
    """Run the Library of Babel server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, LibraryOfBabelHandler)
    
    print(f"📚 Library of Babel API Server")
    print(f"🌐 Running on http://localhost:{port}")
    print(f"📖 Press Ctrl+C to stop")
    print(f"\n🔗 Available endpoints:")
    print(f"   http://localhost:{port}/")
    print(f"   http://localhost:{port}/api/books/random")
    print(f"   http://localhost:{port}/api/books/number/0")
    print(f"   http://localhost:{port}/api/stats")
    print(f"   http://localhost:{port}/api/search?q=abc")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("📚 Library of Babel - Local Server")
    print("=" * 60)
    
    # Test the services first
    print("\n🧪 Testing services...")
    
    try:
        library = Library()
        generator = BookGenerator()
        search = BookSearch()
        
        # Test book generation
        book = generator.generate_by_number(0)
        print(f"✅ Book generation works: {book.book_id[:20]}...")
        
        # Test random book
        random_book = generator.generate_random()
        print(f"✅ Random book works: {random_book.book_id[:20]}...")
        
        # Test search
        results = search.search("a", limit=1)
        print(f"✅ Search works: found {len(results)} results")
        
        # Test library
        stats = library.get_stats()
        print(f"✅ Library works: {stats.cached_books} cached books")
        
        print("\n🎉 All services working!")
        print("\n🚀 Starting server...")
        
        run_server()
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
