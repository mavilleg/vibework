"""
Encoding schemes for the Library of Babel.

This module provides various encoding schemes for converting between book IDs
and book content, including base-25 encoding which is central to Borges' concept.
"""

import math
from typing import List, Optional, Tuple, Union

from ..config import get_config


class EncodingError(Exception):
    """Exception raised for encoding/decoding errors."""
    pass


class Base25Encoder:
    """
    Base-25 encoder for the Library of Babel.
    
    This encoder converts between integers and base-25 representations,
    which is the mathematical foundation of Borges' library. Each book
    can be uniquely identified by a number in the range [0, 25^N) where
    N is the total number of characters in a book.
    
    The alphabet used is: abcdefghijklmnopqrstuvwxyz ,.
    (22 letters + space + comma + period = 25 characters)
    """
    
    def __init__(self, alphabet: Optional[str] = None) -> None:
        """
        Initialize the encoder with a specific alphabet.
        
        Args:
            alphabet: The alphabet to use for encoding (default: standard 25 chars)
        """
        if alphabet is None:
            config = get_config().book
            alphabet = config.alphabet
        
        self.alphabet = alphabet
        self.base = len(alphabet)
        self.char_to_index = {char: idx for idx, char in enumerate(alphabet)}
        self.index_to_char = {idx: char for idx, char in enumerate(alphabet)}
    
    def encode(self, number: int, length: Optional[int] = None) -> str:
        """
        Encode an integer to a base-25 string.
        
        Args:
            number: The integer to encode
            length: Optional fixed length for the result (pad with leading zeros)
        
        Returns:
            The base-25 encoded string
        
        Raises:
            EncodingError: If the number is negative or too large
        """
        if number < 0:
            raise EncodingError("Cannot encode negative numbers")
        
        if number == 0:
            result = self.alphabet[0]
            if length is not None:
                result = self.alphabet[0] * length
            return result
        
        result = []
        while number > 0:
            number, remainder = divmod(number, self.base)
            result.append(self.index_to_char[remainder])
        
        # Reverse to get the correct order
        result.reverse()
        encoded = "".join(result)
        
        # Pad with leading zeros if length is specified
        if length is not None:
            if len(encoded) > length:
                raise EncodingError(
                    f"Number {number} requires {len(encoded)} digits, "
                    f"but length {length} was specified"
                )
            encoded = encoded.rjust(length, self.alphabet[0])
        
        return encoded
    
    def decode(self, encoded: str) -> int:
        """
        Decode a base-25 string to an integer.
        
        Args:
            encoded: The base-25 encoded string
        
        Returns:
            The decoded integer
        
        Raises:
            EncodingError: If the string contains invalid characters
        """
        if not encoded:
            return 0
        
        result = 0
        for char in encoded:
            if char not in self.char_to_index:
                raise EncodingError(f"Invalid character in encoded string: {char}")
            result = result * self.base + self.char_to_index[char]
        
        return result
    
    def encode_book_id(self, book_number: int) -> str:
        """
        Encode a book number to a book ID string.
        
        The book ID is a base-25 string of fixed length equal to the total
        number of characters in a book.
        
        Args:
            book_number: The book number (0 to 25^N - 1)
        
        Returns:
            The book ID string
        """
        config = get_config().book
        return self.encode(book_number, length=config.total_chars)
    
    def decode_book_id(self, book_id: str) -> int:
        """
        Decode a book ID string to a book number.
        
        Args:
            book_id: The book ID string
        
        Returns:
            The book number
        
        Raises:
            EncodingError: If the book ID is invalid
        """
        config = get_config().book
        
        if len(book_id) != config.total_chars:
            raise EncodingError(
                f"Book ID must be exactly {config.total_chars} characters long, "
                f"got {len(book_id)}"
            )
        
        return self.decode(book_id)
    
    def validate_book_id(self, book_id: str) -> bool:
        """
        Validate that a book ID is properly formatted.
        
        Args:
            book_id: The book ID to validate
        
        Returns:
            True if valid, False otherwise
        """
        config = get_config().book
        
        if len(book_id) != config.total_chars:
            return False
        
        for char in book_id:
            if char not in self.char_to_index:
                return False
        
        return True
    
    def get_total_books(self) -> int:
        """
        Get the total number of possible books.
        
        Returns:
            The total number of possible books (25^N)
        """
        config = get_config().book
        return self.base ** config.total_chars
    
    def get_random_book_id(self) -> str:
        """
        Generate a random valid book ID.
        
        Returns:
            A random book ID string
        """
        import random
        config = get_config().book
        return "".join(random.choice(self.alphabet) for _ in range(config.total_chars))


class BookEncoder:
    """
    High-level book encoder that converts between book numbers and book content.
    
    This encoder uses the Base25Encoder to convert book numbers to book IDs,
    and then generates the corresponding book content based on the ID.
    """
    
    def __init__(self) -> None:
        """Initialize the book encoder."""
        self.base25 = Base25Encoder()
        self.config = get_config().book
    
    def number_to_book_id(self, book_number: int) -> str:
        """
        Convert a book number to a book ID.
        
        Args:
            book_number: The book number (0 to 25^N - 1)
        
        Returns:
            The book ID string
        """
        return self.base25.encode_book_id(book_number)
    
    def book_id_to_number(self, book_id: str) -> int:
        """
        Convert a book ID to a book number.
        
        Args:
            book_id: The book ID string
        
        Returns:
            The book number
        """
        return self.base25.decode_book_id(book_id)
    
    def number_to_content(self, book_number: int) -> str:
        """
        Convert a book number directly to book content.
        
        This method generates the content of the book corresponding to the given number.
        The content is generated by treating the book number as a base-25 number and
        converting each digit to the corresponding character in the alphabet.
        
        Args:
            book_number: The book number
        
        Returns:
            The book content as a string
        """
        book_id = self.number_to_book_id(book_number)
        return self.book_id_to_content(book_id)
    
    def book_id_to_content(self, book_id: str) -> str:
        """
        Convert a book ID to book content.
        
        Args:
            book_id: The book ID string
        
        Returns:
            The book content as a string
        
        Raises:
            EncodingError: If the book ID is invalid
        """
        if not self.base25.validate_book_id(book_id):
            raise EncodingError(f"Invalid book ID: {book_id}")
        
        # The book ID itself is the content when interpreted as a sequence of characters
        return book_id
    
    def content_to_book_id(self, content: str) -> str:
        """
        Convert book content to a book ID.
        
        Args:
            content: The book content
        
        Returns:
            The book ID
        
        Raises:
            EncodingError: If the content length is incorrect
        """
        config = get_config().book
        
        if len(content) != config.total_chars:
            raise EncodingError(
                f"Content must be exactly {config.total_chars} characters long, "
                f"got {len(content)}"
            )
        
        # Validate all characters are in the alphabet
        for char in content:
            if char not in self.base25.char_to_index:
                raise EncodingError(f"Invalid character in content: {char}")
        
        return content
    
    def number_to_book(self, book_number: int) -> "Book":
        """
        Convert a book number to a Book object.
        
        Args:
            book_number: The book number
        
        Returns:
            A Book object with the generated content
        """
        from .book import Book
        
        book_id = self.number_to_book_id(book_number)
        content = self.number_to_content(book_number)
        
        return Book(book_id=book_id, content=content)
    
    def book_id_to_book(self, book_id: str) -> "Book":
        """
        Convert a book ID to a Book object.
        
        Args:
            book_id: The book ID string
        
        Returns:
            A Book object with the corresponding content
        """
        from .book import Book
        
        content = self.book_id_to_content(book_id)
        return Book(book_id=book_id, content=content)
    
    def get_neighboring_books(self, book_id: str, count: int = 5) -> List[str]:
        """
        Get book IDs of neighboring books.
        
        Args:
            book_id: The central book ID
            count: Number of neighbors to return on each side
        
        Returns:
            List of neighboring book IDs
        """
        try:
            book_number = self.book_id_to_number(book_id)
        except EncodingError:
            return []
        
        neighbors = []
        for i in range(1, count + 1):
            # Previous books
            if book_number - i >= 0:
                neighbors.append(self.number_to_book_id(book_number - i))
            
            # Next books
            total_books = self.base25.get_total_books()
            if book_number + i < total_books:
                neighbors.append(self.number_to_book_id(book_number + i))
        
        return neighbors
    
    def get_distance(self, book_id1: str, book_id2: str) -> int:
        """
        Calculate the distance between two book IDs.
        
        The distance is the absolute difference between their book numbers.
        
        Args:
            book_id1: First book ID
            book_id2: Second book ID
        
        Returns:
            The distance between the books
        """
        try:
            num1 = self.book_id_to_number(book_id1)
            num2 = self.book_id_to_number(book_id2)
            return abs(num1 - num2)
        except EncodingError:
            return -1
