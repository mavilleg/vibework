"""
Search API routes for the Library of Babel.

This module provides the API endpoints for searching books in the library.
"""

import re
from fastapi import APIRouter, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from ..config import get_config
from ..exceptions import InvalidSearchQueryError, RegexError
from ..monitoring import monitor_api_request

router = APIRouter(prefix="/api/search", tags=["search"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Get services from app state
def get_search_service(request: Request):
    return request.app.state.search_service


@router.get("", response_model=list, summary="Search for books")
@limiter.limit("20/minute")
async def search_books(
    request: Request,
    q: str = Query(..., min_length=1, description="Text to search for"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    strategy: str = Query("sequential", description="Search strategy: sequential, random, or smart")
):
    """
    Search for books containing the specified text.
    
    This endpoint searches through the library for books that contain the
    given query text. Due to the enormous size of the library, the search
    is limited to a reasonable subset of books.
    
    Args:
        q: The text to search for
        limit: Maximum number of results to return
        strategy: Search strategy to use
    
    Returns:
        List of search results with book data and match information
    
    Raises:
        HTTPException: If the search query is invalid
    """
    config = get_config()
    
    # Validate query length
    if not q or len(q.strip()) == 0:
        raise InvalidSearchQueryError(q, "Search query cannot be empty")
    
    if len(q) > config.security.max_query_length:
        raise InvalidSearchQueryError(
            q, 
            f"Search query too long. Maximum length is {config.security.max_query_length} characters."
        )
    
    # Validate strategy
    valid_strategies = ["sequential", "random", "smart"]
    if strategy not in valid_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}"
        )
    
    try:
        search_service = get_search_service(request)
        results = search_service.search(q, limit=limit, strategy=strategy)
        
        return [
            {
                "book_id": result.book.book_id,
                "matches": [
                    {"page": p, "line": l, "position": pos} 
                    for p, l, pos in result.matches
                ],
                "score": result.score,
                "book": result.book.to_dict(),
            }
            for result in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.get("/regex", response_model=list, summary="Search with regular expression")
@limiter.limit("10/minute")
async def search_regex(
    request: Request,
    pattern: str = Query(..., min_length=1, description="Regular expression pattern"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search for books matching a regular expression.
    
    This endpoint searches for books that match the given regex pattern.
    
    Args:
        pattern: The regular expression pattern to search for
        limit: Maximum number of results to return
    
    Returns:
        List of search results with book data and match information
    
    Raises:
        HTTPException: If the regex pattern is invalid
    """
    config = get_config()
    
    # Validate pattern length
    if not pattern or len(pattern.strip()) == 0:
        raise RegexError(pattern, "Pattern cannot be empty")
    
    if len(pattern) > config.security.max_regex_length:
        raise RegexError(
            pattern,
            f"Pattern too long. Maximum length is {config.security.max_regex_length} characters."
        )
    
    # Check for potentially dangerous regex patterns
    dangerous_patterns = [
        r'\.\*',      # .* - can cause catastrophic backtracking
        r'\.\+',      # .+ - can cause catastrophic backtracking
        r'\*\.',      # *. - can cause catastrophic backtracking
        r'\+\.',      # +. - can cause catastrophic backtracking
        r'\{',        # { - quantifier
        r'\}',        # } - quantifier
        r'\(\?',      # (? - lookahead/lookbehind
        r'\[\^',      # [^ - negated character class
    ]
    
    for dangerous in dangerous_patterns:
        if dangerous in pattern:
            raise RegexError(
                pattern,
                f"Pattern contains potentially dangerous construct: {dangerous}"
            )
    
    try:
        # Compile with timeout to prevent ReDoS
        compiled = re.compile(pattern, re.IGNORECASE, timeout=1.0)
    except re.error as e:
        raise RegexError(pattern, str(e))
    except TimeoutError:
        raise RegexError(pattern, "Regex compilation timeout")
    
    try:
        search_service = get_search_service(request)
        results = search_service.search_regex(pattern, limit=limit)
        
        return [
            {
                "book_id": result.book.book_id,
                "matches": [
                    {"page": p, "line": l, "position": pos} 
                    for p, l, pos in result.matches
                ],
                "score": result.score,
                "book": result.book.to_dict(),
            }
            for result in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {e}")


@router.get("/similar/{book_id}", response_model=list, summary="Find similar books")
@limiter.limit("15/minute")
async def find_similar(
    request: Request,
    book_id: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Find books similar to the specified book.
    
    This endpoint finds books that have similar content patterns to the
    given book.
    
    Args:
        book_id: The book ID to find similar books for
        limit: Maximum number of results to return
    
    Returns:
        List of similar books
    
    Raises:
        HTTPException: If the book ID is invalid
    """
    config = get_config()
    
    # Validate book ID
    if len(book_id) != config.book.total_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Book ID must be exactly {config.book.total_chars} characters long"
        )
    
    try:
        search_service = get_search_service(request)
        results = search_service.find_similar(book_id, limit=limit)
        
        return [
            {
                "book_id": result.book.book_id,
                "similarity_score": result.score,
                "book": result.book.to_dict(),
            }
            for result in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid book ID: {e}")
