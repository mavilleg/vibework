"""
Search API routes for the Library of Babel.

This module provides the API endpoints for searching books in the library.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..services.search import BookSearch, SearchResult

router = APIRouter(prefix="/api/search", tags=["search"])

# Initialize search service
search_service = BookSearch()


@router.get("", response_model=list, summary="Search for books")
async def search_books(
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
    if not q or len(q.strip()) == 0:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
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
async def search_regex(
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
    try:
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
async def find_similar(
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
    try:
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
