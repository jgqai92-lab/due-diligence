"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import Base

TEST_DB_URL = "sqlite:///./test_skeptical_analyst.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Reset all rate limiter storage between tests to prevent cross-test pollution
    # Each router may have its own Limiter instance with in-memory storage
    from app.routers import (
        ist as ist_router_mod,
        ist_synthesis as ist_synth_router_mod,
        workflows as wf_router_mod,
        hfrt as hfrt_router_mod,
    )
    for mod in [ist_router_mod, wf_router_mod, ist_synth_router_mod, hfrt_router_mod]:
        if hasattr(mod, "limiter"):
            try:
                mod.limiter.reset()
            except Exception:
                pass
    if hasattr(app.state, "limiter") and app.state.limiter:
        try:
            app.state.limiter.reset()
        except Exception:
            pass

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Sample financial data for unit tests ───────────────────────────

@pytest.fixture
def sample_financials():
    """Two years of income statement data (yfinance format)."""
    return {
        "2024-09-28T00:00:00.000Z": {
            "Total Revenue": 391035000000,
            "Gross Profit": 180683000000,
            "Net Income": 93736000000,
            "EBIT": 123216000000,
            "Selling General And Administration": 26097000000,
            "Depreciation And Amortization": 11519000000,
        },
        "2023-09-30T00:00:00.000Z": {
            "Total Revenue": 383285000000,
            "Gross Profit": 169148000000,
            "Net Income": 96995000000,
            "EBIT": 114301000000,
            "Selling General And Administration": 24932000000,
            "Depreciation And Amortization": 11104000000,
        },
    }


@pytest.fixture
def sample_balance_sheet():
    """Two years of balance sheet data."""
    return {
        "2024-09-28T00:00:00.000Z": {
            "Total Assets": 364980000000,
            "Current Assets": 152987000000,
            "Net PPE": 44856000000,
            "Net Receivables": 66243000000,
            "Total Liabilities Net Minority Interest": 308030000000,
            "Current Liabilities": 176392000000,
            "Retained Earnings": -214460000000,
        },
        "2023-09-30T00:00:00.000Z": {
            "Total Assets": 352583000000,
            "Current Assets": 143566000000,
            "Net PPE": 43715000000,
            "Net Receivables": 60985000000,
            "Total Liabilities Net Minority Interest": 290437000000,
            "Current Liabilities": 145308000000,
            "Retained Earnings": -214460000000,
        },
    }


@pytest.fixture
def sample_cashflow():
    """Cash flow statement data."""
    return {
        "2024-09-28T00:00:00.000Z": {
            "Operating Cash Flow": 118254000000,
            "Capital Expenditure": -9959000000,
        },
        "2023-09-30T00:00:00.000Z": {
            "Operating Cash Flow": 110543000000,
            "Capital Expenditure": -10959000000,
        },
    }


@pytest.fixture
def sample_info():
    """Company info dict."""
    return {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "marketCap": 2890000000000,
        "fullTimeEmployees": 164000,
    }


@pytest.fixture
def sample_quarterly_financials():
    """Two quarters of income statement data."""
    return {
        "2024-09-28T00:00:00.000Z": {
            "Total Revenue": 94930000000,
            "Selling General And Administration": 6523000000,
        },
        "2024-06-29T00:00:00.000Z": {
            "Total Revenue": 85778000000,
            "Selling General And Administration": 6320000000,
        },
    }
