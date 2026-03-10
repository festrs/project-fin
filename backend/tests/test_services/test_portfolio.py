from datetime import date, timedelta

import pytest

from app.models import User, AssetClass, AssetWeight, Transaction
from app.services.portfolio import PortfolioService


def _create_user(db):
    user = User(name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_asset_class(db, user_id, name="Stocks", target_weight=60.0):
    ac = AssetClass(user_id=user_id, name=name, target_weight=target_weight)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _create_asset_weight(db, asset_class_id, symbol, target_weight=50.0):
    aw = AssetWeight(asset_class_id=asset_class_id, symbol=symbol, target_weight=target_weight)
    db.add(aw)
    db.commit()
    db.refresh(aw)
    return aw


def _create_tx(db, user_id, asset_class_id, symbol, tx_type, quantity, unit_price, tx_date=None):
    if tx_date is None:
        tx_date = date.today()
    tx = Transaction(
        user_id=user_id,
        asset_class_id=asset_class_id,
        asset_symbol=symbol,
        type=tx_type,
        quantity=quantity,
        unit_price=unit_price,
        total_value=quantity * unit_price,
        currency="USD",
        date=tx_date,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


class TestGetHoldings:
    def test_get_holdings_two_assets(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id)
        _create_tx(db, user.id, ac.id, "AAPL", "buy", 10, 150.0)
        _create_tx(db, user.id, ac.id, "GOOG", "buy", 5, 200.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 2
        symbols = {h["symbol"] for h in holdings}
        assert symbols == {"AAPL", "GOOG"}

        aapl = next(h for h in holdings if h["symbol"] == "AAPL")
        assert aapl["quantity"] == 10
        assert aapl["avg_price"] == 150.0
        assert aapl["total_cost"] == 1500.0

    def test_get_holdings_with_sells(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id)
        _create_tx(db, user.id, ac.id, "AAPL", "buy", 10, 150.0)
        _create_tx(db, user.id, ac.id, "AAPL", "buy", 5, 160.0)
        _create_tx(db, user.id, ac.id, "AAPL", "sell", 3, 170.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 1
        aapl = holdings[0]
        assert aapl["symbol"] == "AAPL"
        # net quantity = 10 + 5 - 3 = 12
        assert aapl["quantity"] == 12
        # avg buy price = (10*150 + 5*160) / 15 = 2300/15 ≈ 153.33
        assert round(aapl["avg_price"], 2) == 153.33
        # total_cost = avg_price (unrounded) * quantity = (2300/15) * 12 = 1840.0
        assert round(aapl["total_cost"], 2) == 1840.0


class TestGetAllocation:
    def test_get_allocation(self, db):
        user = _create_user(db)
        ac_stocks = _create_asset_class(db, user.id, "Stocks", 60.0)
        ac_crypto = _create_asset_class(db, user.id, "Crypto", 40.0)
        _create_asset_weight(db, ac_stocks.id, "AAPL", 50.0)
        _create_asset_weight(db, ac_stocks.id, "GOOG", 50.0)
        _create_asset_weight(db, ac_crypto.id, "BTC", 100.0)

        _create_tx(db, user.id, ac_stocks.id, "AAPL", "buy", 10, 150.0)
        _create_tx(db, user.id, ac_stocks.id, "GOOG", "buy", 5, 200.0)
        _create_tx(db, user.id, ac_crypto.id, "BTC", "buy", 1, 60000.0)

        svc = PortfolioService(db)
        allocation = svc.get_allocation(user.id)

        assert len(allocation) == 2
        names = {a["class_name"] for a in allocation}
        assert names == {"Stocks", "Crypto"}

        stocks = next(a for a in allocation if a["class_name"] == "Stocks")
        assert stocks["target_weight"] == 60.0
        assert len(stocks["assets"]) == 2

        crypto = next(a for a in allocation if a["class_name"] == "Crypto")
        assert crypto["target_weight"] == 40.0
        assert len(crypto["assets"]) == 1
        assert crypto["assets"][0]["symbol"] == "BTC"
