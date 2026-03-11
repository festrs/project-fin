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
