"""Integration tests for analysis API endpoints."""

from unittest.mock import patch


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAnalyzeEndpoint:
    def test_invalid_ticker_format(self, client):
        resp = client.get("/api/analyze/123INVALID")
        assert resp.status_code == 400

    def test_valid_ticker_format_accepted(self, client):
        """Test that valid format is accepted (may fail on data fetch if no network)."""
        with patch("app.routers.analyze.fetch_financial_data") as mock_fetch:
            mock_fetch.return_value = {
                "info": {"symbol": "TEST", "longName": "Test Corp", "sector": "Tech", "industry": "Software", "marketCap": 1000000},
                "financials": {
                    "2024-01-01": {"Total Revenue": 1000000, "Gross Profit": 600000, "Net Income": 200000, "EBIT": 300000, "Selling General And Administration": 100000, "Depreciation And Amortization": 50000},
                    "2023-01-01": {"Total Revenue": 900000, "Gross Profit": 540000, "Net Income": 180000, "EBIT": 270000, "Selling General And Administration": 95000, "Depreciation And Amortization": 48000},
                },
                "balance_sheet": {
                    "2024-01-01": {"Total Assets": 5000000, "Current Assets": 2000000, "Net PPE": 1000000, "Net Receivables": 500000, "Total Liabilities Net Minority Interest": 3000000, "Current Liabilities": 1000000, "Retained Earnings": 500000},
                    "2023-01-01": {"Total Assets": 4500000, "Current Assets": 1800000, "Net PPE": 950000, "Net Receivables": 450000, "Total Liabilities Net Minority Interest": 2700000, "Current Liabilities": 900000, "Retained Earnings": 400000},
                },
                "cashflow": {
                    "2024-01-01": {"Operating Cash Flow": 400000, "Capital Expenditure": -50000},
                    "2023-01-01": {"Operating Cash Flow": 350000, "Capital Expenditure": -45000},
                },
                "quarterly_financials": {},
                "cache_hit": False,
                "fetched_at": "2026-01-30T12:00:00Z",
                "periods": ["2024-01-01", "2023-01-01"],
            }

            with patch("app.routers.analyze.generate_report") as mock_report:
                from app.schemas.analysis import ForensicReport
                mock_report.return_value = ForensicReport(
                    markdown="## Test Report", generated_at="2026-01-30T12:00:00Z", model="test"
                )
                resp = client.get("/api/analyze/TEST")
                assert resp.status_code == 200
                data = resp.json()
                assert data["ticker"] == "TEST"
                assert "forensic_metrics" in data
                assert "beneish_m_score" in data["forensic_metrics"]


class TestReportEndpoint:
    def test_report_not_found(self, client):
        resp = client.get("/api/analyze/ZZZZ/report")
        assert resp.status_code == 404


class TestSearchEndpoint:
    def test_search_requires_query(self, client):
        resp = client.get("/api/search")
        assert resp.status_code == 422

    def test_search_with_query(self, client):
        with patch("app.routers.search.search_tickers") as mock_search:
            mock_search.return_value = [{"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "stock"}]
            resp = client.get("/api/search?q=AAPL")
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] >= 0
