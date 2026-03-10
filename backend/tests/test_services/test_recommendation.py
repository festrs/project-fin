from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.models import User, AssetClass, AssetWeight, Transaction
from app.services.recommendation import RecommendationService


def _create_user(db):
    user = User(name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_asset_class(db, user_id, name, target_weight):
    ac = AssetClass(user_id=user_id, name=name, target_weight=target_weight)
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


def _create_buy(db, user_id, asset_class_id, symbol, quantity, unit_price, buy_date=None):
    if buy_date is None:
        buy_date = date.today() - timedelta(days=5)
    tx = Transaction(
        user_id=user_id,
        asset_class_id=asset_class_id,
        asset_symbol=symbol,
        type="buy",
        quantity=quantity,
        unit_price=unit_price,
        total_value=quantity * unit_price,
        currency="USD",
        date=buy_date,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _mock_market_data():
    """Return a mock MarketDataService that returns predictable prices."""
    mock = MagicMock()

    def stock_quote(symbol):
        prices = {"AAPL": 150.0, "GOOG": 200.0}
        return {"symbol": symbol, "current_price": prices.get(symbol, 100.0)}

    def crypto_quote(coin_id):
        prices = {"bitcoin": 50000.0}
        return {"coin_id": coin_id, "current_price": prices.get(coin_id, 100.0)}

    mock.get_stock_quote.side_effect = stock_quote
    mock.get_crypto_quote.side_effect = crypto_quote
    return mock


class TestRecommendationService:
    def test_recommend_top_2(self, db):
        """BTC is most underweight and should be first."""
        user = _create_user(db)

        # Stocks class: 60% target, Crypto class: 40% target
        ac_stocks = _create_asset_class(db, user.id, "Stocks", 60.0)
        ac_crypto = _create_asset_class(db, user.id, "Crypto", 40.0)

        # AAPL 50% of Stocks, GOOG 50% of Stocks, BTC 100% of Crypto
        _create_asset_weight(db, ac_stocks.id, "AAPL", 50.0)
        _create_asset_weight(db, ac_stocks.id, "GOOG", 50.0)
        _create_asset_weight(db, ac_crypto.id, "BTC", 100.0)

        # Holdings: AAPL=10 @ 150=$1500 cost, GOOG=5 @ 200=$1000 cost, BTC=0.01 @ 50000=$500 cost
        _create_buy(db, user.id, ac_stocks.id, "AAPL", 10, 150.0)
        _create_buy(db, user.id, ac_stocks.id, "GOOG", 5, 200.0)
        _create_buy(db, user.id, ac_crypto.id, "BTC", 0.01, 50000.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        recs = svc.get_recommendations(user.id, count=2)

        assert len(recs) == 2
        # Current prices: AAPL=10*150=1500, GOOG=5*200=1000, BTC=0.01*50000=500
        # Total = 3000
        # Effective targets: AAPL=60*50/100=30%, GOOG=60*50/100=30%, BTC=40*100/100=40%
        # Actual weights: AAPL=1500/3000*100=50%, GOOG=1000/3000*100=33.33%, BTC=500/3000*100=16.67%
        # Diffs: AAPL=30-50=-20, GOOG=30-33.33=-3.33, BTC=40-16.67=23.33
        # BTC should be first (highest diff), GOOG second
        assert recs[0]["symbol"] == "BTC"
        assert recs[0]["diff"] > 0
        assert recs[1]["symbol"] == "GOOG"

    def test_quarantined_asset_excluded(self, db):
        """BTC with 2 buys should be quarantined and excluded."""
        user = _create_user(db)

        ac_stocks = _create_asset_class(db, user.id, "Stocks", 60.0)
        ac_crypto = _create_asset_class(db, user.id, "Crypto", 40.0)

        _create_asset_weight(db, ac_stocks.id, "AAPL", 50.0)
        _create_asset_weight(db, ac_stocks.id, "GOOG", 50.0)
        _create_asset_weight(db, ac_crypto.id, "BTC", 100.0)

        _create_buy(db, user.id, ac_stocks.id, "AAPL", 10, 150.0)
        _create_buy(db, user.id, ac_stocks.id, "GOOG", 5, 200.0)
        # Two BTC buys within period -> quarantined
        _create_buy(db, user.id, ac_crypto.id, "BTC", 0.005, 50000.0, date.today() - timedelta(days=30))
        _create_buy(db, user.id, ac_crypto.id, "BTC", 0.005, 50000.0, date.today() - timedelta(days=5))

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        recs = svc.get_recommendations(user.id, count=2)

        symbols = [r["symbol"] for r in recs]
        assert "BTC" not in symbols
