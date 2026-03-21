from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import User, AssetClass, AssetWeight, Transaction
from app.money import Money, Currency
from app.services.portfolio import PortfolioService
from app.services.auth import hash_password


def _create_user(db):
    user = User(name="Test User", email="test@example.com", password_hash=hash_password("testpass"))
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
        unit_price=Decimal(str(unit_price)),
        total_value=Decimal(str(quantity)) * Decimal(str(unit_price)),
        currency="USD",
        date=tx_date,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _create_fixed_income_tx(db, user_id, asset_class_id, symbol, tx_type, total_value, tx_date=None):
    if tx_date is None:
        tx_date = date.today()
    tx = Transaction(
        user_id=user_id,
        asset_class_id=asset_class_id,
        asset_symbol=symbol,
        type=tx_type,
        quantity=None,
        unit_price=None,
        total_value=Decimal(str(total_value)),
        currency="BRL",
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
        assert aapl["avg_price"].amount == Decimal("150")
        assert aapl["avg_price"].currency is Currency.USD
        assert aapl["total_cost"].amount == Decimal("1500")
        assert aapl["total_cost"].currency is Currency.USD

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
        assert round(aapl["avg_price"].amount, 2) == Decimal("153.33")
        # total_cost = avg_price (unrounded) * quantity = (2300/15) * 12 = 1840.0
        assert round(aapl["total_cost"].amount, 2) == Decimal("1840.00")
        assert aapl["total_cost"].currency is Currency.USD


    def test_get_holdings_fixed_income(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 10000.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 5000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 1
        cdb = holdings[0]
        assert cdb["symbol"] == "CDB Banco X"
        assert cdb["quantity"] is None
        assert cdb["avg_price"] is None
        assert cdb["total_cost"].amount == Decimal("15000")
        assert cdb["total_cost"].currency is Currency.BRL

    def test_get_holdings_mixed_stock_and_fixed_income(self, db):
        user = _create_user(db)
        ac_stocks = _create_asset_class(db, user.id, "Stocks", 60.0)
        ac_fi = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_tx(db, user.id, ac_stocks.id, "AAPL", "buy", 10, 150.0)
        _create_fixed_income_tx(db, user.id, ac_fi.id, "CDB Banco X", "buy", 10000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 2
        symbols = {h["symbol"] for h in holdings}
        assert symbols == {"AAPL", "CDB Banco X"}

        aapl = next(h for h in holdings if h["symbol"] == "AAPL")
        assert aapl["quantity"] == 10

        cdb = next(h for h in holdings if h["symbol"] == "CDB Banco X")
        assert cdb["quantity"] is None
        assert cdb["total_cost"].amount == Decimal("10000")

    def test_get_holdings_fixed_income_with_sell(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 10000.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "sell", 3000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 1
        cdb = holdings[0]
        assert cdb["total_cost"].amount == Decimal("7000")

    def test_get_holdings_fixed_income_fully_sold(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id, "Renda Fixa", 20.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "buy", 10000.0)
        _create_fixed_income_tx(db, user.id, ac.id, "CDB Banco X", "sell", 10000.0)

        svc = PortfolioService(db)
        holdings = svc.get_holdings(user.id)

        assert len(holdings) == 0


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
