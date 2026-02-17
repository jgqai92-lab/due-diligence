"""Integration tests for portfolio API endpoints."""

from unittest.mock import patch


class TestPortfolioEndpoints:
    def test_list_empty_portfolio(self, client):
        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["holdings"] == []
        assert data["summary"]["holding_count"] == 0

    def test_add_holding(self, client):
        with patch("app.routers.portfolio.get_current_price", return_value=185.0):
            resp = client.post("/api/portfolio", json={
                "ticker": "AAPL",
                "shares": 100,
                "costBasis": 150.0,
                "purchaseDate": "2024-06-15",
            })
            assert resp.status_code == 201
            data = resp.json()
            assert data["ticker"] == "AAPL"
            assert data["shares"] == 100

    def test_add_invalid_ticker(self, client):
        resp = client.post("/api/portfolio", json={
            "ticker": "INVALID123",
            "shares": 100,
            "costBasis": 150.0,
            "purchaseDate": "2024-06-15",
        })
        assert resp.status_code in (400, 422)

    def test_update_holding(self, client):
        with patch("app.routers.portfolio.get_current_price", return_value=185.0):
            # Create first
            resp = client.post("/api/portfolio", json={
                "ticker": "MSFT",
                "shares": 50,
                "costBasis": 300.0,
                "purchaseDate": "2024-01-01",
            })
            holding_id = resp.json()["id"]

            # Update
            resp = client.patch(f"/api/portfolio/{holding_id}", json={"shares": 75})
            assert resp.status_code == 200
            assert resp.json()["shares"] == 75

    def test_delete_holding(self, client):
        with patch("app.routers.portfolio.get_current_price", return_value=185.0):
            resp = client.post("/api/portfolio", json={
                "ticker": "TSLA",
                "shares": 10,
                "costBasis": 200.0,
                "purchaseDate": "2024-03-01",
            })
            holding_id = resp.json()["id"]

            resp = client.delete(f"/api/portfolio/{holding_id}")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Holding deleted"

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/portfolio/9999")
        assert resp.status_code == 404


class TestAlertEndpoints:
    def test_list_empty_alerts(self, client):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alerts"] == []
        assert data["count"] == 0

    def test_dismiss_nonexistent(self, client):
        resp = client.delete("/api/alerts/9999")
        assert resp.status_code == 404


class TestWatchdog:
    def test_watchdog_empty_portfolio(self, client):
        resp = client.get("/api/portfolio/watchdog")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scanned_count"] == 0
