from datetime import date
from unittest.mock import MagicMock

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.models.user import User
from app.services.split_checker_scheduler import SplitCheckerScheduler


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US", type="stock")
    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR", type="stock")
    db.add_all([ac_us, ac_br])
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac_us.id, asset_symbol="FAST",
        type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
        currency="USD", date=date(2025, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
        type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
        currency="BRL", date=date(2025, 1, 1),
    ))
    db.commit()
    return user


class TestSplitCheckerScheduler:
    def test_creates_pending_splits(self, db):
        _setup_holdings(db)
        finnhub = MagicMock()
        brapi = MagicMock()

        finnhub.get_splits.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        splits = db.query(StockSplit).filter(StockSplit.symbol == "FAST").all()
        assert len(splits) == 1
        assert splits[0].status == "pending"
        assert splits[0].from_factor == 1
        assert splits[0].to_factor == 2

    def test_skips_existing_splits(self, db):
        user = _setup_holdings(db)

        ac = db.query(AssetClass).filter(AssetClass.name == "US Stocks").first()
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="pending", asset_class_id=ac.id,
        ))
        db.commit()

        finnhub = MagicMock()
        brapi = MagicMock()
        finnhub.get_splits.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        splits = db.query(StockSplit).filter(StockSplit.symbol == "FAST").all()
        assert len(splits) == 1  # no duplicate

    def test_continues_on_provider_error(self, db):
        _setup_holdings(db)
        finnhub = MagicMock()
        brapi = MagicMock()

        finnhub.get_splits.side_effect = Exception("API error")
        brapi.get_splits.return_value = [
            {"symbol": "PETR4.SA", "date": "2008-03-24", "fromFactor": 1, "toFactor": 2},
        ]

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        splits = db.query(StockSplit).all()
        assert len(splits) == 1
        assert splits[0].symbol == "PETR4.SA"

    def test_uses_correct_provider_by_suffix(self, db):
        _setup_holdings(db)
        finnhub = MagicMock()
        brapi = MagicMock()
        finnhub.get_splits.return_value = []
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        finnhub.get_splits.assert_called_once()
        assert finnhub.get_splits.call_args[0][0] == "FAST"
        brapi.get_splits.assert_called_once()
        assert brapi.get_splits.call_args[0][0] == "PETR4.SA"
