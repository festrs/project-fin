from datetime import date

import pytest

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.models.user import User
from app.services.portfolio import PortfolioService


def _make_user(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()
    return user


def _make_stock_class(db, user):
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US", type="stock")
    db.add(ac)
    db.flush()
    return ac


class TestSplitAwareHoldings:
    def test_no_splits_no_regression(self, db):
        """Existing behavior: no splits applied, quantities unchanged."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
            type="buy", quantity=100, unit_price=150.0, total_value=15000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        assert len(holdings) == 1
        assert holdings[0]["quantity"] == 100
        assert holdings[0]["avg_price"] == 150.0

    def test_simple_split_no_sells(self, db):
        """Buy 100 @ $60, split 1:2 -> 200 shares, avg $30."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 200
        assert h["avg_price"] == pytest.approx(30.0)
        assert h["total_cost"] == pytest.approx(6000.0)

    def test_split_with_pre_split_sells(self, db):
        """Buy 200 @ $60, sell 100, split 1:2 -> 200 shares, avg $30, cost $6000."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=200, unit_price=60.0, total_value=12000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="sell", quantity=100, unit_price=65.0, total_value=6500.0,
            currency="USD", date=date(2025, 3, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 200  # (200*2) - (100*2) = 200
        assert h["avg_price"] == pytest.approx(30.0)  # 12000 / 400
        assert h["total_cost"] == pytest.approx(6000.0)

    def test_split_with_post_split_sells(self, db):
        """Buy 100 @ $60, split 1:2, sell 50 -> 150 shares, avg $30."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="sell", quantity=50, unit_price=32.0, total_value=1600.0,
            currency="USD", date=date(2025, 6, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 150  # (100*2) - (50*1)
        assert h["avg_price"] == pytest.approx(30.0)
        assert h["total_cost"] == pytest.approx(4500.0)

    def test_multiple_splits(self, db):
        """Buy 100 @ $120, split 1:2, then split 1:3 -> 600 shares, avg $20."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=120.0, total_value=12000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 9, 1),
            from_factor=1, to_factor=3, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 600  # 100 * 2 * 3
        assert h["avg_price"] == pytest.approx(20.0)  # 12000 / 600

    def test_pending_split_not_applied(self, db):
        """Pending splits should NOT affect holdings."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="pending", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 100  # unchanged
        assert h["avg_price"] == 60.0

    def test_dismissed_split_not_applied(self, db):
        """Dismissed splits should NOT affect holdings."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="dismissed", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 100
