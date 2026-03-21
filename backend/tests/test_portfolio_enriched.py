from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.money import Money, Currency
from app.services.market_data import MarketDataService


def test_get_quote_safe_returns_none_on_error():
    service = MarketDataService()
    with patch.object(service, "get_stock_quote", side_effect=Exception("network error")):
        result = service.get_quote_safe("INVALID", is_crypto=False)
        assert result is None


def test_get_quote_safe_returns_price_for_stock():
    service = MarketDataService()
    mock_quote = {"current_price": Money(Decimal("150"), Currency.USD)}
    with patch.object(service, "get_stock_quote", return_value=mock_quote):
        result = service.get_quote_safe("AAPL", is_crypto=False)
        assert result == Money(Decimal("150"), Currency.USD)


def test_get_quote_safe_returns_price_for_crypto():
    service = MarketDataService()
    mock_quote = {"current_price": Money(Decimal("95000"), Currency.USD)}
    with patch.object(service, "get_crypto_quote", return_value=mock_quote):
        result = service.get_quote_safe("bitcoin", is_crypto=True)
        assert result == Money(Decimal("95000"), Currency.USD)


from app.services.portfolio import PortfolioService


def test_enrich_holdings_adds_current_price():
    holdings = [
        {"symbol": "AAPL", "asset_class_id": "cls-1", "quantity": 10, "avg_price": Money(Decimal("100"), Currency.USD), "total_cost": Money(Decimal("1000"), Currency.USD), "currency": Currency.USD},
        {"symbol": "GOOG", "asset_class_id": "cls-1", "quantity": 5, "avg_price": Money(Decimal("200"), Currency.USD), "total_cost": Money(Decimal("1000"), Currency.USD), "currency": Currency.USD},
    ]
    class_map = {
        "cls-1": {"name": "Stocks US", "target_weight": 50.0},
    }
    weight_map = {"AAPL": 50.0, "GOOG": 50.0}

    def mock_safe(symbol, is_crypto=False, country="US", db=None, db_only=False):
        prices = {"AAPL": Money(Decimal("150"), Currency.USD), "GOOG": Money(Decimal("300"), Currency.USD)}
        return prices.get(symbol)

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", side_effect=mock_safe):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    assert result[0]["current_price"] == Money(Decimal("150"), Currency.USD)
    assert result[0]["current_value"] == Money(Decimal("1500"), Currency.USD)
    assert result[0]["gain_loss"] == Money(Decimal("500"), Currency.USD)  # (150 - 100) * 10
    assert result[1]["current_price"] == Money(Decimal("300"), Currency.USD)
    assert result[1]["current_value"] == Money(Decimal("1500"), Currency.USD)
    assert result[1]["gain_loss"] == Money(Decimal("500"), Currency.USD)


def test_enrich_holdings_handles_failed_price_fetch():
    holdings = [
        {"symbol": "INVALID", "asset_class_id": "cls-1", "quantity": 10, "avg_price": Money(Decimal("100"), Currency.USD), "total_cost": Money(Decimal("1000"), Currency.USD), "currency": Currency.USD},
    ]
    class_map = {"cls-1": {"name": "Stocks US", "target_weight": 50.0}}
    weight_map = {"INVALID": 100.0}

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", return_value=None):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    assert result[0]["current_price"] is None
    assert result[0]["current_value"] is None
    assert result[0]["gain_loss"] is None


def test_enrich_holdings_calculates_weights():
    holdings = [
        {"symbol": "AAPL", "asset_class_id": "cls-1", "quantity": 10, "avg_price": Money(Decimal("100"), Currency.USD), "total_cost": Money(Decimal("1000"), Currency.USD), "currency": Currency.USD},
        {"symbol": "GOOG", "asset_class_id": "cls-1", "quantity": 10, "avg_price": Money(Decimal("100"), Currency.USD), "total_cost": Money(Decimal("1000"), Currency.USD), "currency": Currency.USD},
    ]
    class_map = {"cls-1": {"name": "Stocks US", "target_weight": 50.0}}
    weight_map = {"AAPL": 60.0, "GOOG": 40.0}

    def mock_safe(symbol, is_crypto=False, country="US", db=None, db_only=False):
        return Money(Decimal("100"), Currency.USD)  # same price for both

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", side_effect=mock_safe):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    # target_weight = class_weight * asset_weight / 100 = 50 * 60 / 100 = 30
    assert result[0]["target_weight"] == 30.0
    assert result[1]["target_weight"] == 20.0
    # actual_weight = (current_value / total_portfolio_value) * 100 = (1000 / 2000) * 100 = 50
    assert result[0]["actual_weight"] == 50.0
    assert result[1]["actual_weight"] == 50.0


from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import create_access_token

client = TestClient(app)


def test_portfolio_summary_returns_enriched_holdings():
    """Integration test: summary endpoint returns current_price field."""
    token = create_access_token("test-user-enriched-id")
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.routers.portfolio.get_market_data_service") as mock_get:
        mock_instance = MagicMock()
        mock_instance.get_quote_safe.return_value = Money(Decimal("150"), Currency.USD)
        mock_get.return_value = mock_instance

        resp = client.get("/api/portfolio/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "holdings" in data
        for h in data["holdings"]:
            assert "current_price" in h
            assert "current_value" in h
            assert "gain_loss" in h
            assert "target_weight" in h
            assert "actual_weight" in h
