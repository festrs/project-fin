from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.money import Currency, Money
from app.services.auth import create_access_token


def _setup_holdings(db, user_id):
    """Create asset classes and transactions for testing movers."""
    ac_us = AssetClass(user_id=user_id, name="US Stocks", country="US", target_weight=50.0)
    ac_br = AssetClass(user_id=user_id, name="BR Stocks", country="BR", target_weight=50.0)
    db.add_all([ac_us, ac_br])
    db.flush()

    tx1 = Transaction(
        user_id=user_id,
        asset_class_id=ac_us.id,
        asset_symbol="AAPL",
        type="buy",
        quantity=10,
        unit_price=Decimal("150.00"),
        total_value=Decimal("1500.00"),
        currency="USD",
        tax_amount=Decimal("0"),
        date=date(2025, 1, 1),
    )
    tx2 = Transaction(
        user_id=user_id,
        asset_class_id=ac_us.id,
        asset_symbol="MSFT",
        type="buy",
        quantity=5,
        unit_price=Decimal("400.00"),
        total_value=Decimal("2000.00"),
        currency="USD",
        tax_amount=Decimal("0"),
        date=date(2025, 1, 1),
    )
    tx3 = Transaction(
        user_id=user_id,
        asset_class_id=ac_br.id,
        asset_symbol="PETR4.SA",
        type="buy",
        quantity=100,
        unit_price=Decimal("30.00"),
        total_value=Decimal("3000.00"),
        currency="BRL",
        tax_amount=Decimal("0"),
        date=date(2025, 1, 1),
    )
    db.add_all([tx1, tx2, tx3])
    db.commit()
    return ac_us, ac_br


@patch("app.routers.market.fetch_exchange_rate")
@patch("app.routers.market.get_market_data_service")
def test_get_indices(mock_get_mds, mock_fx, client):
    mock_md = MagicMock()

    def fake_quote(symbol, country, db):
        if symbol == "^BVSP":
            return {
                "symbol": "^BVSP",
                "name": "Ibovespa",
                "current_price": Money(Decimal("128000.00"), Currency.BRL),
                "currency": Currency.BRL,
                "market_cap": Money(Decimal("0"), Currency.BRL),
            }
        elif symbol == "SPY":
            return {
                "symbol": "SPY",
                "name": "SPDR S&P 500",
                "current_price": Money(Decimal("520.00"), Currency.USD),
                "currency": Currency.USD,
                "market_cap": Money(Decimal("0"), Currency.USD),
            }
        raise ValueError(f"Unknown symbol: {symbol}")

    mock_md.get_stock_quote.side_effect = fake_quote
    mock_get_mds.return_value = mock_md
    mock_fx.return_value = 5.25

    resp = client.get("/api/market/indices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3

    assert data[0]["symbol"] == "IBOV"
    assert data[0]["value"] == "128000.00"
    assert data[0]["change_pct"] is None

    assert data[1]["symbol"] == "S&P 500"
    assert data[1]["value"] == "520.00"

    assert data[2]["symbol"] == "USD/BRL"
    assert data[2]["value"] == "5.25"


@patch("app.routers.market.get_market_data_service")
def test_get_movers(mock_get_mds, client, default_user, db, auth_headers):
    _setup_holdings(db, default_user.id)

    mock_md = MagicMock()

    def fake_quote(symbol, country, db_session):
        quotes = {
            "AAPL": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "current_price": Money(Decimal("180.00"), Currency.USD),  # +20% from 150
                "currency": Currency.USD,
                "market_cap": Money(Decimal("0"), Currency.USD),
            },
            "MSFT": {
                "symbol": "MSFT",
                "name": "Microsoft Corp.",
                "current_price": Money(Decimal("360.00"), Currency.USD),  # -10% from 400
                "currency": Currency.USD,
                "market_cap": Money(Decimal("0"), Currency.USD),
            },
            "PETR4.SA": {
                "symbol": "PETR4.SA",
                "name": "Petrobras",
                "current_price": Money(Decimal("33.00"), Currency.BRL),  # +10% from 30
                "currency": Currency.BRL,
                "market_cap": Money(Decimal("0"), Currency.BRL),
            },
        }
        return quotes[symbol]

    mock_md.get_stock_quote.side_effect = fake_quote
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/market/movers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["gainers"]) == 2
    assert data["gainers"][0]["symbol"] == "AAPL"
    assert data["gainers"][0]["change_pct"] == 20.0
    assert data["gainers"][1]["symbol"] == "PETR4.SA"
    assert data["gainers"][1]["change_pct"] == 10.0

    assert len(data["losers"]) == 1
    assert data["losers"][0]["symbol"] == "MSFT"
    assert data["losers"][0]["change_pct"] == -10.0


def test_get_movers_empty(client, default_user, auth_headers):
    resp = client.get("/api/market/movers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["gainers"] == []
    assert data["losers"] == []
