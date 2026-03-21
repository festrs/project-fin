from datetime import date
from unittest.mock import MagicMock, patch

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth import hash_password
from app.services.split_checker_scheduler import SplitCheckerScheduler


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com", password_hash=hash_password("testpass"))
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
    @patch("app.services.split_checker_scheduler.YFinanceProvider")
    def test_creates_pending_splits(self, mock_yf_cls, db):
        _setup_holdings(db)
        mock_yf = mock_yf_cls.return_value
        brapi = MagicMock()

        mock_yf.get_splits.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        splits = db.query(StockSplit).filter(StockSplit.symbol == "FAST").all()
        assert len(splits) == 1
        assert splits[0].status == "pending"
        assert splits[0].from_factor == 1
        assert splits[0].to_factor == 2

    @patch("app.services.split_checker_scheduler.YFinanceProvider")
    def test_skips_existing_splits(self, mock_yf_cls, db):
        user = _setup_holdings(db)
        mock_yf = mock_yf_cls.return_value
        brapi = MagicMock()

        ac = db.query(AssetClass).filter(AssetClass.name == "US Stocks").first()
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="pending", asset_class_id=ac.id,
        ))
        db.commit()

        mock_yf.get_splits.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        splits = db.query(StockSplit).filter(StockSplit.symbol == "FAST").all()
        assert len(splits) == 1  # no duplicate

    @patch("app.services.split_checker_scheduler.YFinanceProvider")
    def test_continues_on_provider_error(self, mock_yf_cls, db):
        _setup_holdings(db)
        mock_yf = mock_yf_cls.return_value
        brapi = MagicMock()

        mock_yf.get_splits.side_effect = Exception("API error")
        mock_dados = MagicMock()
        mock_dados.scrape_splits.return_value = [
            {"symbol": "PETR4.SA", "date": "2025-06-15", "fromFactor": 1, "toFactor": 2},
        ]

        scheduler = SplitCheckerScheduler(brapi_provider=brapi, delay=0)
        scheduler._dados = mock_dados
        scheduler.check_all(db)

        splits = db.query(StockSplit).all()
        assert len(splits) == 1
        assert splits[0].symbol == "PETR4.SA"

    @patch("app.services.split_checker_scheduler.YFinanceProvider")
    def test_uses_dados_de_mercado_for_br_stocks(self, mock_yf_cls, db):
        _setup_holdings(db)
        mock_yf = mock_yf_cls.return_value
        brapi = MagicMock()
        mock_yf.get_splits.return_value = []
        mock_dados = MagicMock()
        mock_dados.scrape_splits.return_value = []

        scheduler = SplitCheckerScheduler(brapi_provider=brapi, delay=0)
        scheduler._dados = mock_dados
        scheduler.check_all(db)

        mock_yf.get_splits.assert_called_once()
        assert mock_yf.get_splits.call_args[0][0] == "FAST"
        mock_dados.scrape_splits.assert_called_once()
        assert mock_dados.scrape_splits.call_args[0][0] == "PETR4.SA"

    @patch("app.services.split_checker_scheduler.YFinanceProvider")
    def test_skips_splits_older_than_3_years(self, mock_yf_cls, db):
        _setup_holdings(db)
        mock_yf = mock_yf_cls.return_value
        brapi = MagicMock()
        mock_yf.get_splits.return_value = []
        mock_dados = MagicMock()
        mock_dados.scrape_splits.return_value = [
            {"symbol": "PETR4.SA", "date": "2008-03-24", "fromFactor": 1, "toFactor": 2},
        ]

        scheduler = SplitCheckerScheduler(brapi_provider=brapi, delay=0)
        scheduler._dados = mock_dados
        scheduler.check_all(db)

        splits = db.query(StockSplit).all()
        assert len(splits) == 0
