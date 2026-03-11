from unittest.mock import patch, MagicMock
from app.services.market_data import MarketDataService


def test_get_quote_safe_returns_none_on_error():
    service = MarketDataService()
    with patch.object(service, "get_stock_quote", side_effect=Exception("network error")):
        result = service.get_quote_safe("INVALID", is_crypto=False)
        assert result is None


def test_get_quote_safe_returns_price_for_stock():
    service = MarketDataService()
    mock_quote = {"current_price": 150.0}
    with patch.object(service, "get_stock_quote", return_value=mock_quote):
        result = service.get_quote_safe("AAPL", is_crypto=False)
        assert result == 150.0


def test_get_quote_safe_returns_price_for_crypto():
    service = MarketDataService()
    mock_quote = {"current_price": 95000.0}
    with patch.object(service, "get_crypto_quote", return_value=mock_quote):
        result = service.get_quote_safe("bitcoin", is_crypto=True)
        assert result == 95000.0


from app.services.portfolio import PortfolioService


def test_enrich_holdings_adds_current_price():
    holdings = [
        {"symbol": "AAPL", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
        {"symbol": "GOOG", "asset_class_id": "cls-1", "quantity": 5, "avg_price": 200.0, "total_cost": 1000.0},
    ]
    class_map = {
        "cls-1": {"name": "Stocks US", "target_weight": 50.0},
    }
    weight_map = {"AAPL": 50.0, "GOOG": 50.0}

    def mock_safe(symbol, is_crypto=False):
        prices = {"AAPL": 150.0, "GOOG": 300.0}
        return prices.get(symbol)

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", side_effect=mock_safe):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    assert result[0]["current_price"] == 150.0
    assert result[0]["current_value"] == 1500.0
    assert result[0]["gain_loss"] == 500.0  # (150 - 100) * 10
    assert result[1]["current_price"] == 300.0
    assert result[1]["current_value"] == 1500.0
    assert result[1]["gain_loss"] == 500.0


def test_enrich_holdings_handles_failed_price_fetch():
    holdings = [
        {"symbol": "INVALID", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
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
        {"symbol": "AAPL", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
        {"symbol": "GOOG", "asset_class_id": "cls-1", "quantity": 10, "avg_price": 100.0, "total_cost": 1000.0},
    ]
    class_map = {"cls-1": {"name": "Stocks US", "target_weight": 50.0}}
    weight_map = {"AAPL": 60.0, "GOOG": 40.0}

    def mock_safe(symbol, is_crypto=False):
        return 100.0  # same price for both

    market_data = MarketDataService()
    with patch.object(market_data, "get_quote_safe", side_effect=mock_safe):
        result = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)

    # target_weight = class_weight * asset_weight / 100 = 50 * 60 / 100 = 30
    assert result[0]["target_weight"] == 30.0
    assert result[1]["target_weight"] == 20.0
    # actual_weight = (current_value / total_portfolio_value) * 100 = (1000 / 2000) * 100 = 50
    assert result[0]["actual_weight"] == 50.0
    assert result[1]["actual_weight"] == 50.0
