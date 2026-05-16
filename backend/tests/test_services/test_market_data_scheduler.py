from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.market_quote import MarketQuote
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.models.user import User
from app.money import Money, Currency
from app.services.market_data import MarketDataService
from app.services.market_data_scheduler import MarketDataScheduler
from app.services.auth import hash_password


@pytest.fixture
def service():
    svc = MarketDataService()
    svc._yfinance = MagicMock()
    svc._finnhub = MagicMock()
    svc._brapi = MagicMock()
    svc._quote_cache.clear()
    return svc


@pytest.fixture
def scheduler(service):
    return MarketDataScheduler(market_data_service=service)


def _setup_user_with_holdings(db):
    user = User(name="Test", email="test@test.com", password_hash=hash_password("testpass"))
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
    def test_fetches_via_yfinance_and_persists_yield(self, scheduler, service, db):
        _setup_user_with_holdings(db)

        def yf_quote(sym):
            if sym == "AAPL":
                return {
                    "symbol": "AAPL", "name": "Apple",
                    "current_price": Money(Decimal("175.0"), Currency.USD),
                    "currency": Currency.USD,
                    "market_cap": Money(Decimal("2800000000000"), Currency.USD),
                    "dividend_yield": Decimal("0.39"),
                }
            return {
                "symbol": "PETR4.SA", "name": "Petrobras",
                "current_price": Money(Decimal("40.0"), Currency.BRL),
                "currency": Currency.BRL,
                "market_cap": Money(Decimal("500000000000"), Currency.BRL),
                "dividend_yield": Decimal("7.96"),
            }
        service._yfinance.get_quote.side_effect = yf_quote

        scheduler.fetch_all_quotes(db)

        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl.current_price == Decimal("175.0")
        assert aapl.country == "US"
        assert aapl.dividend_yield == Decimal("0.39")

        petr = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
        assert petr.current_price == Decimal("40.0")
        assert petr.country == "BR"
        assert petr.dividend_yield == Decimal("7.96")

    def test_falls_back_to_finnhub_when_yfinance_fails(self, scheduler, service, db):
        _setup_user_with_holdings(db)

        service._yfinance.get_quote.side_effect = Exception("yahoo down")
        service._finnhub.get_quote.return_value = {
            "symbol": "AAPL", "name": "Apple",
            "current_price": Money(Decimal("175.0"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("2800000000000"), Currency.USD),
        }
        service._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras",
            "current_price": Money(Decimal("40.0"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }

        scheduler.fetch_all_quotes(db)

        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl.current_price == Decimal("175.0")
        assert aapl.dividend_yield is None  # fallback didn't supply yield

    def test_cron_bypasses_ttl_cache(self, scheduler, service, db):
        """Cron must always reach the live provider, never the in-process cache."""
        _setup_user_with_holdings(db)
        # Pre-seed cache with a stale value the cron must NOT use.
        service._quote_cache["AAPL"] = {
            "symbol": "AAPL", "name": "Stale",
            "current_price": Money(Decimal("1.00"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("0"), Currency.USD),
            "dividend_yield": None,
        }
        service._yfinance.get_quote.return_value = {
            "symbol": "AAPL", "name": "Apple",
            "current_price": Money(Decimal("175.0"), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal("2800000000000"), Currency.USD),
            "dividend_yield": Decimal("0.39"),
        }
        service._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras",
            "current_price": Money(Decimal("40.0"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }

        scheduler.fetch_all_quotes(db)

        aapl = db.query(MarketQuote).filter_by(symbol="AAPL").first()
        assert aapl.current_price == Decimal("175.0"), "cron used cache instead of live"
        assert aapl.name == "Apple"

    def test_continues_on_individual_failure(self, scheduler, service, db):
        _setup_user_with_holdings(db)

        # yfinance fails for both; finnhub also fails for AAPL
        service._yfinance.get_quote.side_effect = Exception("yahoo down")
        service._finnhub.get_quote.side_effect = Exception("finnhub down")
        service._brapi.get_quote.return_value = {
            "symbol": "PETR4.SA", "name": "Petrobras",
            "current_price": Money(Decimal("40.0"), Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("500000000000"), Currency.BRL),
        }

        scheduler.fetch_all_quotes(db)

        assert db.query(MarketQuote).filter_by(symbol="AAPL").first() is None
        assert db.query(MarketQuote).filter_by(symbol="PETR4.SA").first() is not None
