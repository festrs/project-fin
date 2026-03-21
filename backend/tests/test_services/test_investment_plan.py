from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models import User, AssetClass, AssetWeight, Transaction
from app.money import Money, Currency
from app.services.recommendation import RecommendationService


def _create_user(db):
    user = User(name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_asset_class(db, user_id, name, target_weight, country="US", asset_type="stock"):
    ac = AssetClass(user_id=user_id, name=name, target_weight=target_weight, country=country, type=asset_type)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _create_asset_weight(db, asset_class_id, symbol, target_weight):
    aw = AssetWeight(asset_class_id=asset_class_id, symbol=symbol, target_weight=target_weight)
    db.add(aw)
    db.commit()
    db.refresh(aw)
    return aw


def _create_buy(db, user_id, asset_class_id, symbol, quantity, unit_price, currency="USD"):
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    tx = Transaction(
        user_id=user_id,
        asset_class_id=asset_class_id,
        asset_symbol=symbol,
        type="buy",
        quantity=qty,
        unit_price=price,
        total_value=qty * price,
        currency=currency,
        date=date.today() - timedelta(days=5),
    )
    db.add(tx)
    db.commit()
    return tx


def _mock_market_data():
    mock = MagicMock()

    def stock_quote(symbol, country="US", db=None):
        prices = {
            "AAPL": Money(Decimal("150.0"), Currency.USD),
            "GOOG": Money(Decimal("200.0"), Currency.USD),
            "PETR4.SA": Money(Decimal("40.0"), Currency.BRL),
        }
        return {"symbol": symbol, "current_price": prices.get(symbol, Money(Decimal("100.0"), Currency.USD))}

    def crypto_quote(coin_id):
        prices = {"bitcoin": Money(Decimal("50000.0"), Currency.USD)}
        return {"coin_id": coin_id, "current_price": prices.get(coin_id, Money(Decimal("100.0"), Currency.USD))}

    mock.get_stock_quote.side_effect = stock_quote
    mock.get_crypto_quote.side_effect = crypto_quote
    return mock


class TestGetInvestmentPlan:
    def test_distributes_amount_across_underweight_assets(self, db):
        """Should distribute USD amount proportionally by gap, returning quantities."""
        user = _create_user(db)

        ac_stocks = _create_asset_class(db, user.id, "Stocks", 60.0)
        ac_crypto = _create_asset_class(db, user.id, "Crypto", 40.0, asset_type="crypto")

        _create_asset_weight(db, ac_stocks.id, "AAPL", 50.0)
        _create_asset_weight(db, ac_stocks.id, "GOOG", 50.0)
        _create_asset_weight(db, ac_crypto.id, "BTC", 100.0)

        _create_buy(db, user.id, ac_stocks.id, "AAPL", 10, 150.0)
        _create_buy(db, user.id, ac_stocks.id, "GOOG", 5, 200.0)
        _create_buy(db, user.id, ac_crypto.id, "BTC", 0.01, 50000.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("3000"), "USD", count=3)

        assert len(plan["recommendations"]) > 0
        for rec in plan["recommendations"]:
            assert rec["quantity"] > 0
            assert rec["invest_amount"].amount > 0
            assert rec["price"].amount > 0

        total = plan["total_invested"].amount + plan["remainder"].amount
        assert total == Decimal("3000")

    def test_stocks_get_whole_share_quantities(self, db):
        """Stock quantities should be rounded down to whole numbers."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "US Stocks", 100.0)
        _create_asset_weight(db, ac.id, "AAPL", 100.0)
        _create_buy(db, user.id, ac.id, "AAPL", 10, 150.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("400"), "USD", count=1)

        rec = plan["recommendations"][0]
        assert rec["symbol"] == "AAPL"
        assert rec["quantity"] == 2
        assert rec["invest_amount"].amount == Decimal("300")
        assert plan["remainder"].amount == Decimal("100")

    def test_crypto_gets_fractional_quantity(self, db):
        """Crypto quantities should be fractional."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "Crypto", 100.0, asset_type="crypto")
        _create_asset_weight(db, ac.id, "BTC", 100.0)
        _create_buy(db, user.id, ac.id, "BTC", 0.01, 50000.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("1000"), "USD", count=1)

        rec = plan["recommendations"][0]
        assert rec["symbol"] == "BTC"
        assert rec["quantity"] == Decimal("0.02")
        assert plan["remainder"].amount == Decimal("0")

    def test_remainder_redistribution(self, db):
        """Remainder from rounding should be redistributed to buy more shares of other assets."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "Stocks", 100.0)
        _create_asset_weight(db, ac.id, "AAPL", 60.0)
        _create_asset_weight(db, ac.id, "GOOG", 40.0)
        _create_buy(db, user.id, ac.id, "AAPL", 5, 150.0)
        _create_buy(db, user.id, ac.id, "GOOG", 3, 200.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("1000"), "USD", count=2)

        total_invested = sum(r["invest_amount"].amount for r in plan["recommendations"])
        assert total_invested + plan["remainder"].amount == Decimal("1000")
        assert plan["remainder"].amount < Decimal("150")

    def test_currency_conversion_brl_input(self, db):
        """When user inputs BRL, US stock amounts should be converted."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "US Stocks", 100.0)
        _create_asset_weight(db, ac.id, "AAPL", 100.0)
        _create_buy(db, user.id, ac.id, "AAPL", 10, 150.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("1500"), "BRL", count=1, exchange_rate=Decimal("5.0"))

        rec = plan["recommendations"][0]
        assert rec["quantity"] == 2
        assert rec["invest_amount"].currency == Currency.BRL
        assert plan["exchange_rate"] == 5.0
        assert plan["exchange_rate_pair"] == "USD-BRL"

    def test_empty_portfolio_returns_empty(self, db):
        """No holdings should return empty recommendations."""
        user = _create_user(db)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("1000"), "USD", count=3)

        assert plan["recommendations"] == []

    def test_fixed_income_lump_sum(self, db):
        """Fixed income assets should get quantity=1 and lump-sum amount."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "Fixed Income", 100.0, asset_type="fixed_income")
        _create_asset_weight(db, ac.id, "CDB Banco X", 100.0)
        tx = Transaction(
            user_id=user.id,
            asset_class_id=ac.id,
            asset_symbol="CDB Banco X",
            type="buy",
            quantity=None,
            unit_price=None,
            total_value=Decimal("10000"),
            currency="BRL",
            date=date.today() - timedelta(days=5),
        )
        db.add(tx)
        db.commit()

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("5000"), "BRL", count=1)

        assert len(plan["recommendations"]) == 1
        rec = plan["recommendations"][0]
        assert rec["symbol"] == "CDB Banco X"
        assert rec["quantity"] == 1
