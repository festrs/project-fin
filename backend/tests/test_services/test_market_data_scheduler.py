from decimal import Decimal
from unittest.mock import patch, MagicMock, call

import pytest

from app.models.market_quote import MarketQuote
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.models.user import User
from app.money import Money, Currency
from app.services.market_data_scheduler import MarketDataScheduler


@pytest.fixture
def scheduler():
    finnhub = MagicMock()
    brapi = MagicMock()
    return MarketDataScheduler(finnhub_provider=finnhub, brapi_provider=brapi)


def _setup_user_with_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US")
    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR")
    db.add_all([ac_us, ac_br])
    db.flush()

    from datetime import date
    tx1 = Transaction(
        user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
        type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
        currency="USD", date=date(2025, 1, 1),
    )
    tx2 = Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
        type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
        currency="BRL", date=date(2025, 1, 1),
    )
    db.add_all([tx1, tx2])
    db.commit()
    return user


class TestFetchAllQuotes:
    def test_fetches_and_stores_quotes(self, scheduler, db):
        _setup_user_with_holdings(db)

        scheduler._finnhub.get_quote.return_value = {
            "symbol": "AAPL", "name": "Apple",
            "current_price": Money(Decimal("175.0"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("2800000000000"), Currency.USD),
        }
        scheduler._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras",
            "current_price": Money(Decimal("40.0"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }

        scheduler.fetch_all_quotes(db)

        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl is not None
        assert aapl.current_price == Decimal("175.0")
        assert aapl.country == "US"

        petr = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
        assert petr is not None
        assert petr.current_price == Decimal("40.0")
        assert petr.country == "BR"

    def test_continues_on_individual_failure(self, scheduler, db):
        _setup_user_with_holdings(db)

        scheduler._finnhub.get_quote.side_effect = Exception("Finnhub down")
        scheduler._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras",
            "current_price": Money(Decimal("40.0"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }

        scheduler.fetch_all_quotes(db)

        # AAPL should not be stored
        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl is None

        # PETR4.SA should still be stored
        petr = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
        assert petr is not None

    def test_upserts_existing_quotes(self, scheduler, db):
        _setup_user_with_holdings(db)

        # Pre-existing quote
        old = MarketQuote(symbol="AAPL", name="Apple", current_price=Decimal("170.0"), currency="USD", country="US")
        db.add(old)
        db.commit()

        scheduler._finnhub.get_quote.return_value = {
            "symbol": "AAPL", "name": "Apple Inc",
            "current_price": Money(Decimal("175.0"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("2800000000000"), Currency.USD),
        }
        scheduler._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras",
            "current_price": Money(Decimal("40.0"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }

        scheduler.fetch_all_quotes(db)

        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl.current_price == Decimal("175.0")
        assert aapl.name == "Apple Inc"
