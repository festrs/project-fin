from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction
from app.models.user import User
from app.providers.common import DividendRecord
from app.services.dividend_scraper_scheduler import DividendScheduler


@pytest.fixture
def dados_provider():
    return MagicMock()


@pytest.fixture
def yfinance_provider():
    return MagicMock()


@pytest.fixture
def scheduler(dados_provider, yfinance_provider):
    return DividendScheduler(
        dados_provider=dados_provider,
        yfinance_provider=yfinance_provider,
        br_delay=0.0,
        us_delay=0.0,
    )


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR")
    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=30.0, country="US")
    ac_crypto = AssetClass(user_id=user.id, name="Crypto", target_weight=20.0, country="US")
    db.add_all([ac_br, ac_us, ac_crypto])
    db.flush()

    db.add_all([
        Transaction(
            user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
            type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
            currency="BRL", date=date(2025, 1, 1),
        ),
        Transaction(
            user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
            type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
            currency="USD", date=date(2025, 1, 1),
        ),
        Transaction(
            user_id=user.id, asset_class_id=ac_crypto.id, asset_symbol="BTC",
            type="buy", quantity=1, unit_price=50000.0, total_value=50000.0,
            currency="USD", date=date(2025, 1, 1),
        ),
    ])
    db.commit()


class TestDividendScheduler:
    def test_scrapes_br_with_dados_and_us_with_yfinance(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        dados_provider.scrape_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        br_symbols = [c.args[0] for c in dados_provider.scrape_dividends.call_args_list]
        us_symbols = [c.args[0] for c in yfinance_provider.get_dividends.call_args_list]

        assert set(br_symbols) == {"PETR4.SA"}
        assert set(us_symbols) == {"AAPL"}
        # Crypto excluded
        assert "BTC" not in br_symbols + us_symbols

    def test_stores_us_dividends(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        dados_provider.scrape_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=0.25,
                record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
                payment_date=None,
            ),
        ]

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="AAPL").all()
        assert len(records) == 1
        assert records[0].value == 0.25
        assert records[0].dividend_type == "Dividend"
        assert records[0].payment_date is None

    def test_stores_br_dividends(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        dados_provider.scrape_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividendo", value=1.50,
                record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
                payment_date=date(2025, 11, 28),
            ),
        ]
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1

    def test_skips_existing_duplicates(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        db.add(DividendHistory(
            symbol="AAPL", dividend_type="Dividend", value=0.25,
            record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
            payment_date=None,
        ))
        db.commit()

        dados_provider.scrape_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=0.25,
                record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
                payment_date=None,
            ),
        ]

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="AAPL").all()
        assert len(records) == 1
