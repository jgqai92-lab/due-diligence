"""Unit tests for yfinance_service: caching, fetching, and search."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.cached_financials import CachedFinancial
from app.services.yfinance_service import (
    _df_to_json,
    _get_cached,
    _store_cache,
    fetch_financial_data,
    clear_cache,
    search_tickers,
)


# ── Test DB setup ────────────────────────────────────────────────────────────

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ── _df_to_json ──────────────────────────────────────────────────────────────


class TestDfToJson:
    """Tests for _df_to_json()."""

    def test_none_returns_empty_dict(self):
        assert _df_to_json(None) == "{}"

    def test_empty_dataframe(self):
        mock_df = MagicMock()
        mock_df.empty = True
        assert _df_to_json(mock_df) == "{}"

    def test_valid_dataframe(self):
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.to_json.return_value = '{"col": {"row": 1}}'
        result = _df_to_json(mock_df)
        assert result == '{"col": {"row": 1}}'
        mock_df.to_json.assert_called_once_with(date_format="iso")


# ── _get_cached / _store_cache ───────────────────────────────────────────────


class TestCacheOperations:
    """Tests for _get_cached and _store_cache."""

    def test_get_cached_returns_none_when_empty(self, db):
        assert _get_cached(db, "AAPL", "financials") is None

    def test_store_and_retrieve(self, db):
        _store_cache(db, "AAPL", "financials", '{"revenue": 100}')
        result = _get_cached(db, "AAPL", "financials")
        assert result == '{"revenue": 100}'

    def test_get_cached_returns_none_when_expired(self, db):
        # Manually insert an expired entry
        db.add(CachedFinancial(
            ticker="AAPL",
            data_type="financials",
            raw_json='{"old": true}',
            fetched_at=datetime.utcnow() - timedelta(hours=48),
            expires_at=datetime.utcnow() - timedelta(hours=1),
        ))
        db.commit()
        assert _get_cached(db, "AAPL", "financials") is None

    def test_store_cache_upserts_existing(self, db):
        _store_cache(db, "AAPL", "financials", '{"v": 1}')
        _store_cache(db, "AAPL", "financials", '{"v": 2}')
        result = _get_cached(db, "AAPL", "financials")
        assert result == '{"v": 2}'
        count = db.query(CachedFinancial).filter(
            CachedFinancial.ticker == "AAPL",
            CachedFinancial.data_type == "financials",
        ).count()
        assert count == 1

    def test_store_cache_different_types(self, db):
        _store_cache(db, "AAPL", "financials", '{"f": 1}')
        _store_cache(db, "AAPL", "balance_sheet", '{"b": 1}')
        assert _get_cached(db, "AAPL", "financials") == '{"f": 1}'
        assert _get_cached(db, "AAPL", "balance_sheet") == '{"b": 1}'


# ── clear_cache ──────────────────────────────────────────────────────────────


class TestClearCache:
    """Tests for clear_cache()."""

    def test_clear_returns_count(self, db):
        _store_cache(db, "AAPL", "financials", '{}')
        _store_cache(db, "AAPL", "balance_sheet", '{}')
        deleted = clear_cache(db, "AAPL")
        assert deleted == 2

    def test_clear_empty_returns_zero(self, db):
        assert clear_cache(db, "AAPL") == 0

    def test_clear_does_not_affect_other_tickers(self, db):
        _store_cache(db, "AAPL", "financials", '{}')
        _store_cache(db, "MSFT", "financials", '{}')
        clear_cache(db, "AAPL")
        assert _get_cached(db, "MSFT", "financials") == '{}'


# ── search_tickers ───────────────────────────────────────────────────────────


class TestSearchTickers:
    """Tests for search_tickers()."""

    def test_empty_query_returns_empty(self):
        assert search_tickers("") == []
        assert search_tickers("   ") == []

    def test_none_like_empty(self):
        assert search_tickers("") == []

    @patch("app.services.yfinance_service.yf.Search")
    def test_search_returns_results(self, mock_search_cls):
        mock_search = MagicMock()
        mock_search.quotes = [
            {
                "symbol": "AAPL",
                "longname": "Apple Inc.",
                "exchange": "NMS",
                "quoteType": "EQUITY",
            },
        ]
        mock_search_cls.return_value = mock_search

        results = search_tickers("apple")
        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"
        assert results[0]["name"] == "Apple Inc."
        assert results[0]["type"] == "equity"

    @patch("app.services.yfinance_service.yf.Search")
    def test_search_no_results(self, mock_search_cls):
        mock_search = MagicMock()
        mock_search.quotes = []
        mock_search_cls.return_value = mock_search
        assert search_tickers("xyznonexistent") == []

    @patch("app.services.yfinance_service.yf.Search")
    def test_search_handles_exception(self, mock_search_cls):
        mock_search_cls.side_effect = Exception("Network error")
        assert search_tickers("apple") == []

    @patch("app.services.yfinance_service.yf.Search")
    def test_search_fallback_shortname(self, mock_search_cls):
        mock_search = MagicMock()
        mock_search.quotes = [
            {"symbol": "TST", "shortname": "Test Co", "exchange": "NYSE"},
        ]
        mock_search_cls.return_value = mock_search
        results = search_tickers("test")
        assert results[0]["name"] == "Test Co"


# ── fetch_financial_data ─────────────────────────────────────────────────────


class TestFetchFinancialData:
    """Tests for fetch_financial_data()."""

    @patch("app.services.yfinance_service.yf.Ticker")
    def test_all_cached(self, mock_ticker_cls, db):
        """When all data types are cached, returns cache_hit=True."""
        for dt in [
            "financials", "balance_sheet", "cashflow",
            "quarterly_financials", "quarterly_balance_sheet",
            "quarterly_cashflow", "info",
        ]:
            _store_cache(db, "AAPL", dt, '{"data": true}')

        result = fetch_financial_data(db, "AAPL")
        assert result["cache_hit"] is True
        # yf.Ticker is still called for potential non-cached fetches
        mock_ticker_cls.assert_called_once_with("AAPL")

    @patch("app.services.yfinance_service.yf.Ticker")
    def test_force_refresh_bypasses_cache(self, mock_ticker_cls, db):
        _store_cache(db, "AAPL", "info", '{"cached": true}')

        mock_ticker = MagicMock()
        mock_ticker.info = {"fresh": True}
        mock_ticker.financials = None
        mock_ticker.balance_sheet = None
        mock_ticker.cashflow = None
        mock_ticker.quarterly_financials = None
        mock_ticker.quarterly_balance_sheet = None
        mock_ticker.quarterly_cashflow = None
        mock_ticker_cls.return_value = mock_ticker

        result = fetch_financial_data(db, "AAPL", force_refresh=True)
        assert result["cache_hit"] is False
        assert result["info"]["fresh"] is True

    @patch("app.services.yfinance_service.yf.Ticker")
    def test_fetch_failure_returns_empty_dict(self, mock_ticker_cls, db):
        mock_ticker = MagicMock()
        mock_ticker.info = {"symbol": "AAPL"}
        # financials raises an exception
        type(mock_ticker).financials = property(
            lambda self: (_ for _ in ()).throw(Exception("API error"))
        )
        mock_ticker.balance_sheet = None
        mock_ticker.cashflow = None
        mock_ticker.quarterly_financials = None
        mock_ticker.quarterly_balance_sheet = None
        mock_ticker.quarterly_cashflow = None
        mock_ticker_cls.return_value = mock_ticker

        result = fetch_financial_data(db, "AAPL")
        assert result["financials"] == {}  # Failed gracefully

    @patch("app.services.yfinance_service.yf.Ticker")
    def test_periods_extracted_from_financials(self, mock_ticker_cls, db):
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        fin_mock = MagicMock()
        fin_mock.empty = False
        fin_mock.to_json.return_value = json.dumps({
            "2024-01-01": {"Revenue": 100},
            "2023-01-01": {"Revenue": 90},
        })
        mock_ticker.financials = fin_mock
        mock_ticker.balance_sheet = None
        mock_ticker.cashflow = None
        mock_ticker.quarterly_financials = None
        mock_ticker.quarterly_balance_sheet = None
        mock_ticker.quarterly_cashflow = None
        mock_ticker_cls.return_value = mock_ticker

        result = fetch_financial_data(db, "AAPL")
        assert len(result["periods"]) == 2

    @patch("app.services.yfinance_service.yf.Ticker")
    def test_fetched_at_included(self, mock_ticker_cls, db):
        for dt in [
            "financials", "balance_sheet", "cashflow",
            "quarterly_financials", "quarterly_balance_sheet",
            "quarterly_cashflow", "info",
        ]:
            _store_cache(db, "AAPL", dt, '{}')

        result = fetch_financial_data(db, "AAPL")
        assert "fetched_at" in result
        assert result["fetched_at"].endswith("Z")
