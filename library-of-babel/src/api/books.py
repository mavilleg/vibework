"""
Book API routes for the Library of Babel.

This module provides the API endpoints for retrieving and exploring books.
"""

from fastapi import APIRouter, HTTPException, Query
from ..models.encoding import EncodingError
from ..services.generation import BookGenerator
from ..services.cache import create_cache

router = APIRouter(prefix="/api/books", tags=["books"])

# Initialize services
generator = BookGenerator()
cache = create_cache()


@router.get("/number/{book_number}", response_model=dict, summary="Get a book by number")
async def get_book_by_number(book_number: int):
    """
    Retrieve a specific book by its number.
    
    The book number is an integer in the range [0, 25^N) where N is the
    total number of characters in a book.
    
    Args:
        book_number: The book number
    
    Returns:
        The book data including content, pages, and metadata
    
    Raises:
        HTTPException: If the book number is invalid
    """
    try:
        book = generator.generate_by_number(book_number)
        
        # Cache the book
        cache.set(book.book_id, book)
        
        return book.to_dict()
        
    except EncodingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate book: {e}")


@router.get("/random", response_model=dict, summary="Get a random book")
async def get_random_book():
    """
    Get a random book from the library.
    
    This endpoint returns a randomly selected book from the Library of Babel.
    Each call returns a different random book.
    
    Returns:
        The book data including content, pages, and metadata
    """
    try:
        book = generator.generate_random()
        
        # Cache the book
        cache.set(book.book_id, book)
        
        return book.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate random book: {e}")


@router.get("/range", response_model=list, summary="Get a range of books")
async def get_book_range(
    start: int = Query(0, ge=0, description="Starting book number (inclusive)"),
    end: int = Query(10, gt=0, description="Ending book number (exclusive)")
):
    """
    Get a range of books.
    
    This endpoint returns multiple books in a specified range.
    
    Args:
        start: Starting book number (inclusive)
        end: Ending book number (exclusive)
    
    Returns:
        List of book data
    
    Raises:
        HTTPException: If the range is invalid
    """
    if end <= start:
        raise HTTPException(status_code=400, detail="End must be greater than start")
    
    if end - start > 100:
        raise HTTPException(
            status_code=400, 
            detail="Range too large. Maximum range size is 100 books."
        )
    
    try:
        books = generator.generate_range(start, end)
        
        # Cache all books
        for book in books:
            cache.set(book.book_id, book)
        
        return [book.to_dict() for book in books]
        
    except EncodingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate book range: {e}")


@router.get("/special", response_model=list, summary="Get special books")
async def get_special_books():
    """
    Get a collection of special/interesting books.
    
    This endpoint returns a curated collection of special books including:
    - Book 0 (all 'a's)
    - Book 1 (mostly 'a's with one 'b')
    - Books with all same characters
    - Random books
    
    Returns:
        List of special book data
    """
    try:
        books = generator.generate_special_books()
        
        # Cache all books
        for book in books:
            cache.set(book.book_id, book)
        
        return [book.to_dict() for book in books]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate special books: {e}")


@router.get("/{book_id}", response_model=dict, summary="Get a book by ID")
async def get_book_by_id(book_id: str):
    """
    Retrieve a specific book by its identifier.
    
    The book ID is a base-25 encoded string that uniquely identifies
    a book in the Library of Babel.
    
    Args:
        book_id: The unique book identifier
    
    Returns:
        The book data including content, pages, and metadata
    
    Raises:
        HTTPException: If the book ID is invalid
    """
    # Check cache first
    cached_book = cache.get(book_id)
    if cached_book:
        return cached_book.to_dict()
    
    try:
        book = generator.generate_by_id(book_id)
        
        # Cache the book
        cache.set(book_id, book)
        
        return book.to_dict()
        
    except EncodingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate book: {e}")


@router.get("/{book_id}/page/{page_num}", response_model=dict, summary="Get a specific page")
async def get_book_page(book_id: str, page_num: int):
    """
    Get a specific page from a book.
    
    Args:
        book_id: The book identifier
        page_num: The page number (1-indexed)
    
    Returns:
        The page data including lines
    
    Raises:
        HTTPException: If the book or page is not found
    """
    try:
        # Check cache first
        cached_book = cache.get(book_id)
        if cached_book:
            book = cached_book
        else:
            book = generator.generate_by_id(book_id)
            cache.set(book_id, book)
        
        page = book.get_page(page_num)
        
        return {
            "book_id": book.book_id,
            "page_number": page_num,
            "lines": page,
            "line_count": len(page),
        }
        
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EncodingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get page: {e}")


@router.get("/{book_id}/neighbors", response_model=list, summary="Get neighboring books")
async def get_neighbors(
    book_id: str,
    count: int = Query(5, ge=1, le=20, description="Number of neighbors on each side")
):
    """
    Get books neighboring the specified book.
    
    This returns books that are "close" to the specified book in the
    library's ordering.
    
    Args:
        book_id: The central book identifier
        count: Number of neighbors to return on each side
    
    Returns:
        List of neighboring book data
    
    Raises:
        HTTPException: If the book ID is invalid
    """
    try:
        from ..models.encoding import BookEncoder
        encoder = BookEncoder()
        
        neighbor_ids = encoder.get_neighboring_books(book_id, count)
        
        books = []
        for neighbor_id in neighbor_ids:
            # Check cache first
            cached_book = cache.get(neighbor_id)
            if cached_book:
                books.append(cached_book)
            else:
                book = generator.generate_by_id(neighbor_id)
                cache.set(neighbor_id, book)
                books.append(book)
        
        return [book.to_dict() for book in books]
        
    except EncodingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get neighbors: {e}")


@router.get("/{book_id}/distance/{other_book_id}", response_model=dict, summary="Get distance between books")
async def get_distance(book_id: str, other_book_id: str):
    """
    Calculate the distance between two books.
    
    The distance is the absolute difference between their book numbers.
    
    Args:
        book_id: First book identifier
        other_book_id: Second book identifier
    
    Returns:
        The distance between the books
    
    Raises:
        HTTPException: If either book ID is invalid
    """
    try:
        from ..models.encoding import BookEncoder
        encoder = BookEncoder()
        
        distance = encoder.get_distance(book_id, other_book_id)
        
        return {
            "book_id_1": book_id,
            "book_id_2": other_book_id,
            "distance": distance,
        }
        
    except EncodingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate distance: {e}")
