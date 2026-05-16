from datetime import date
from decimal import Decimal

import pytest

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.models.user import User
from app.money import Money, Currency
from app.services.portfolio import PortfolioService
from app.services.auth import hash_password


def _make_user(db):
    user = User(name="Test", email="test@test.com", password_hash=hash_password("testpass"))
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
            type="buy", quantity=100, unit_price=Decimal("150"), total_value=Decimal("15000"),
            currency="USD", date=date(2025, 1, 1),
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        assert len(holdings) == 1
        assert holdings[0]["quantity"] == 100
        assert holdings[0]["avg_price"].amount == Decimal("150")
        assert holdings[0]["avg_price"].currency is Currency.USD

    # Note: split-aware math used to live inside PortfolioService.get_holdings,
    # which inspected StockSplit(status="applied") rows. The flow has since
    # moved to /api/splits/{id}/apply, which materializes the extra shares as
    # a plain buy Transaction (price 0). The service simply sums transactions
    # now. End-to-end coverage of "apply → holdings reflect split" lives in
    # tests/test_routers/test_splits.py (TestSplitsRouter.test_apply_split).
    # The pending/dismissed cases below still belong here since they assert
    # that orphaned StockSplit rows don't leak into holdings math.

    def test_pending_split_not_applied(self, db):
        """Pending splits should NOT affect holdings."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=Decimal("60"), total_value=Decimal("6000"),
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
        assert h["avg_price"].amount == Decimal("60")

    def test_dismissed_split_not_applied(self, db):
        """Dismissed splits should NOT affect holdings."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=Decimal("60"), total_value=Decimal("6000"),
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
