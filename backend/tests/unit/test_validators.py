"""Tests for input validators."""

import pytest
from app.utils.validators import validate_ticker


class TestValidateTicker:
    def test_valid_tickers(self):
        assert validate_ticker("AAPL") == "AAPL"
        assert validate_ticker("MSFT") == "MSFT"
        assert validate_ticker("A") == "A"
        assert validate_ticker("GOOGL") == "GOOGL"

    def test_lowercase_converted(self):
        assert validate_ticker("aapl") == "AAPL"
        assert validate_ticker("msft") == "MSFT"

    def test_whitespace_stripped(self):
        assert validate_ticker("  AAPL  ") == "AAPL"

    def test_invalid_too_long(self):
        with pytest.raises(ValueError):
            validate_ticker("TOOLONG")

    def test_invalid_numbers(self):
        with pytest.raises(ValueError):
            validate_ticker("AAP1")

    def test_invalid_special_chars(self):
        with pytest.raises(ValueError):
            validate_ticker("AA-PL")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            validate_ticker("")

    def test_spaces_only(self):
        with pytest.raises(ValueError):
            validate_ticker("   ")
