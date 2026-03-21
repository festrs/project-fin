from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models.asset_class import AssetClass
from app.models.fundamentals_score import FundamentalsScore
from app.models.transaction import Transaction
from app.models.user import User
from app.services.fundamentals_scheduler import FundamentalsScoreScheduler
from app.services.auth import hash_password


@pytest.fixture
def yfinance_provider():
    return MagicMock()


@pytest.fixture
def brapi_provider():
    return MagicMock()


@pytest.fixture
def dados_provider():
    return MagicMock()


@pytest.fixture
def scheduler(yfinance_provider, brapi_provider, dados_provider):
    return FundamentalsScoreScheduler(
        yfinance_provider=yfinance_provider,
        brapi_provider=brapi_provider,
        dados_provider=dados_provider,
        delay=0.0,
    )


MOCK_FUNDAMENTALS = {
    "ipo_years": 15,
    "eps_history": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    "net_income_history": [10.0, 20.0, 15.0, 25.0, 30.0, 35.0],
    "debt_history": [1.0, 2.0, 1.5, 2.5, 1.0, 1.2],
    "current_net_debt_ebitda": 1.2,
    "raw_data": [{"year": y, "eps": e} for y, e in zip(range(2020, 2026), [1, 2, 3, 4, 5, 6])],
}


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com", password_hash=hash_password("testpass"))
    db.add(user)
    db.flush()

    ac_us = AssetClass(
        user_id=user.id, name="US Stocks", target_weight=40.0, country="US"
    )
    ac_br = AssetClass(
        user_id=user.id, name="BR Stocks", target_weight=40.0, country="BR"
    )
    ac_crypto = AssetClass(
        user_id=user.id, name="Crypto", target_weight=20.0, country="US"
    )
    db.add_all([ac_us, ac_br, ac_crypto])
    db.flush()

    tx_us = Transaction(
        user_id=user.id,
        asset_class_id=ac_us.id,
        asset_symbol="AAPL",
        type="buy",
        quantity=10,
        unit_price=150.0,
        total_value=1500.0,
        currency="USD",
        date=date(2025, 1, 1),
    )
    tx_br = Transaction(
        user_id=user.id,
        asset_class_id=ac_br.id,
        asset_symbol="PETR4.SA",
        type="buy",
        quantity=100,
        unit_price=38.0,
        total_value=3800.0,
        currency="BRL",
        date=date(2025, 1, 1),
    )
    tx_crypto = Transaction(
        user_id=user.id,
        asset_class_id=ac_crypto.id,
        asset_symbol="BTC",
        type="buy",
        quantity=1,
        unit_price=50000.0,
        total_value=50000.0,
        currency="USD",
        date=date(2025, 1, 1),
    )
    db.add_all([tx_us, tx_br, tx_crypto])
    db.commit()


class TestFundamentalsScheduler:
    def test_discovers_us_and_br_stocks_only(
        self, scheduler, yfinance_provider, brapi_provider, dados_provider, db
    ):
        _setup_holdings(db)

        yfinance_provider.get_fundamentals.return_value = MOCK_FUNDAMENTALS
        brapi_provider.get_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        yfinance_called_symbols = [
            call.args[0] for call in yfinance_provider.get_fundamentals.call_args_list
        ]
        brapi_called_symbols = [
            call.args[0] for call in brapi_provider.get_fundamentals.call_args_list
        ]

        assert "AAPL" in yfinance_called_symbols
        assert "PETR4.SA" in brapi_called_symbols
        assert "BTC" not in yfinance_called_symbols
        assert "BTC" not in brapi_called_symbols

    def test_upserts_score_to_db(
        self, scheduler, yfinance_provider, brapi_provider, dados_provider, db
    ):
        _setup_holdings(db)

        yfinance_provider.get_fundamentals.return_value = MOCK_FUNDAMENTALS
        brapi_provider.get_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        score = db.query(FundamentalsScore).filter_by(symbol="AAPL").first()
        assert score is not None
        assert score.composite_score == 100
        assert score.ipo_rating == "green"

    def test_falls_back_to_dados_for_br(
        self, scheduler, yfinance_provider, brapi_provider, dados_provider, db
    ):
        _setup_holdings(db)

        yfinance_provider.get_fundamentals.return_value = MOCK_FUNDAMENTALS
        # brapi returns insufficient eps_history (fewer than 5 entries)
        brapi_provider.get_fundamentals.return_value = {
            **MOCK_FUNDAMENTALS,
            "eps_history": [],
        }
        dados_provider.scrape_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        dados_provider.scrape_fundamentals.assert_called_once_with("PETR4.SA")

        score = db.query(FundamentalsScore).filter_by(symbol="PETR4.SA").first()
        assert score is not None
        assert score.composite_score == 100

    def test_continues_on_individual_failure(
        self, scheduler, yfinance_provider, brapi_provider, dados_provider, db
    ):
        _setup_holdings(db)

        yfinance_provider.get_fundamentals.side_effect = Exception("Network error")
        brapi_provider.get_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        aapl_score = db.query(FundamentalsScore).filter_by(symbol="AAPL").first()
        assert aapl_score is None

        petr_score = db.query(FundamentalsScore).filter_by(symbol="PETR4.SA").first()
        assert petr_score is not None
        assert petr_score.composite_score == 100
