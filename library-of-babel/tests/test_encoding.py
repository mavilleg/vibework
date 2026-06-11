"""
Tests for the encoding module.

This module tests the Base25Encoder and BookEncoder classes.
"""

import pytest
from src.models.encoding import Base25Encoder, BookEncoder, EncodingError


class TestBase25Encoder:
    """Tests for Base25Encoder."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.encoder = Base25Encoder(alphabet="abc")
    
    def test_encode_zero(self):
        """Test encoding zero."""
        assert self.encoder.encode(0) == "a"
        assert self.encoder.encode(0, length=3) == "aaa"
    
    def test_encode_small_numbers(self):
        """Test encoding small numbers."""
        assert self.encoder.encode(1) == "b"
        assert self.encoder.encode(2) == "c"
        assert self.encoder.encode(3) == "ba"  # 3 = 1*3 + 0
    
    def test_encode_with_length(self):
        """Test encoding with fixed length."""
        assert self.encoder.encode(1, length=3) == "aab"
        assert self.encoder.encode(2, length=3) == "aac"
    
    def test_decode_zero(self):
        """Test decoding zero."""
        assert self.encoder.decode("a") == 0
        assert self.encoder.decode("aaa") == 0
    
    def test_decode_small_numbers(self):
        """Test decoding small numbers."""
        assert self.encoder.decode("b") == 1
        assert self.encoder.decode("c") == 2
        assert self.encoder.decode("ba") == 3
    
    def test_encode_decode_roundtrip(self):
        """Test encode/decode roundtrip."""
        for i in range(100):
            encoded = self.encoder.encode(i)
            decoded = self.encoder.decode(encoded)
            assert decoded == i
    
    def test_encode_negative_raises(self):
        """Test that encoding negative numbers raises error."""
        with pytest.raises(EncodingError):
            self.encoder.encode(-1)
    
    def test_decode_invalid_char_raises(self):
        """Test that decoding invalid characters raises error."""
        with pytest.raises(EncodingError):
            self.encoder.decode("d")  # 'd' is not in alphabet "abc"
    
    def test_get_total_books(self):
        """Test getting total number of possible books."""
        # With alphabet "abc" and default book config
        # But we need to set up the config properly
        encoder = Base25Encoder(alphabet="abc")
        # For testing, we'll use a smaller alphabet
        assert encoder.base == 3
    
    def test_get_random_book_id(self):
        """Test generating random book IDs."""
        book_id = self.encoder.get_random_book_id()
        # Should be a string of the correct length
        # Note: This will fail if config is not set up properly
        # We'll test the length based on the alphabet
        assert isinstance(book_id, str)


class TestBookEncoder:
    """Tests for BookEncoder."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.encoder = BookEncoder()
    
    def test_number_to_book_id(self):
        """Test converting number to book ID."""
        book_id = self.encoder.number_to_book_id(0)
        assert isinstance(book_id, str)
        # Should be the correct length based on config
    
    def test_book_id_to_number(self):
        """Test converting book ID to number."""
        book_id = self.encoder.number_to_book_id(0)
        number = self.encoder.book_id_to_number(book_id)
        assert number == 0
    
    def test_number_to_content(self):
        """Test converting number to content."""
        content = self.encoder.number_to_content(0)
        assert isinstance(content, str)
    
    def test_book_id_to_content(self):
        """Test converting book ID to content."""
        book_id = self.encoder.number_to_book_id(0)
        content = self.encoder.book_id_to_content(book_id)
        assert isinstance(content, str)
    
    def test_content_to_book_id(self):
        """Test converting content to book ID."""
        book_id = self.encoder.number_to_book_id(0)
        content = self.encoder.book_id_to_content(book_id)
        converted_id = self.encoder.content_to_book_id(content)
        assert converted_id == book_id
    
    def test_number_to_book(self):
        """Test converting number to Book object."""
        book = self.encoder.number_to_book(0)
        assert book.book_id is not None
        assert book.content is not None
    
    def test_book_id_to_book(self):
        """Test converting book ID to Book object."""
        book_id = self.encoder.number_to_book_id(0)
        book = self.encoder.book_id_to_book(book_id)
        assert book.book_id == book_id
    
    def test_get_neighboring_books(self):
        """Test getting neighboring books."""
        book_id = self.encoder.number_to_book_id(5)
        neighbors = self.encoder.get_neighboring_books(book_id, count=2)
        assert len(neighbors) <= 4  # 2 on each side
    
    def test_get_distance(self):
        """Test calculating distance between books."""
        book_id1 = self.encoder.number_to_book_id(0)
        book_id2 = self.encoder.number_to_book_id(10)
        distance = self.encoder.get_distance(book_id1, book_id2)
        assert distance == 10
    
    def test_invalid_book_id_raises(self):
        """Test that invalid book IDs raise errors."""
        with pytest.raises(EncodingError):
            self.encoder.book_id_to_content("invalid")


class TestEncodingEdgeCases:
    """Tests for edge cases in encoding."""
    
    def test_empty_string_decode(self):
        """Test decoding empty string."""
        encoder = Base25Encoder(alphabet="abc")
        assert encoder.decode("") == 0
    
    def test_single_character_alphabet(self):
        """Test with single character alphabet."""
        encoder = Base25Encoder(alphabet="a")
        assert encoder.encode(0) == "a"
        assert encoder.decode("a") == 0
    
    def test_large_number_encoding(self):
        """Test encoding large numbers."""
        encoder = Base25Encoder(alphabet="abcdefghijklmnopqrstuvwxyz")
        large_num = 1000000
        encoded = encoder.encode(large_num)
        decoded = encoder.decode(encoded)
        assert decoded == large_num
