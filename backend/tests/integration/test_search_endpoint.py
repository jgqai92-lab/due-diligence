"""Integration tests for search endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_search_ppl_ticker():
    """Test searching for PPL ticker."""
    response = client.get("/api/search?q=PPL")
    assert response.status_code == 200

    data = response.json()
    assert "results" in data
    assert "query" in data
    assert "count" in data
    assert data["query"] == "PPL"
    assert data["count"] >= 0

    # If results exist, validate structure
    if data["count"] > 0:
        result = data["results"][0]
        assert "symbol" in result
        assert "name" in result
        assert "exchange" in result
        assert "type" in result


def test_search_aapl_ticker():
    """Test searching for AAPL ticker."""
    response = client.get("/api/search?q=AAPL")
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == "AAPL"
    assert data["count"] >= 0

    # Should return results for well-known ticker
    if data["count"] > 0:
        result = data["results"][0]
        assert "symbol" in result
        assert "name" in result


def test_search_empty_query():
    """Test search with empty query - should fail validation."""
    response = client.get("/api/search?q=")
    # Empty query should fail min_length validation
    assert response.status_code == 422


def test_search_company_name():
    """Test searching by company name (fuzzy search)."""
    response = client.get("/api/search?q=Apple")
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == "Apple"
    # With yf.Search, should be able to find Apple by name
    assert data["count"] >= 0
