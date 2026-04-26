from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction
from app.models.user import User
from app.providers.brapi import BrapiFeatureUnavailable
from app.providers.common import DividendRecord
from app.services.dividend_scraper_scheduler import DividendScheduler
from app.services.auth import hash_password


@pytest.fixture
def dados_provider():
    return MagicMock()


@pytest.fixture
def yfinance_provider():
    return MagicMock()


@pytest.fixture
def brapi_provider():
    return MagicMock()


@pytest.fixture
def scheduler(dados_provider, yfinance_provider, brapi_provider):
    return DividendScheduler(
        dados_provider=dados_provider,
        yfinance_provider=yfinance_provider,
        brapi_provider=brapi_provider,
        br_delay=0.0,
        us_delay=0.0,
    )


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com", password_hash=hash_password("testpass"))
    db.add(user)
    db.flush()

    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=40.0, country="BR")
    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=30.0, country="US")
    ac_crypto = AssetClass(user_id=user.id, name="Crypto", target_weight=20.0, country="US")
    ac_fii = AssetClass(user_id=user.id, name="FIIs", target_weight=10.0, country="BR")
    db.add_all([ac_br, ac_us, ac_crypto, ac_fii])
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
        Transaction(
            user_id=user.id, asset_class_id=ac_fii.id, asset_symbol="HGLG11.SA",
            type="buy", quantity=200, unit_price=160.0, total_value=32000.0,
            currency="BRL", date=date(2025, 1, 1),
        ),
    ])
    db.commit()


class TestDividendScheduler:
    def test_br_uses_brapi_first_us_uses_yfinance(self, scheduler, brapi_provider, yfinance_provider, db):
        _setup_holdings(db)

        brapi_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=Decimal("1.0"),
                record_date=date(2025, 5, 1), ex_date=date(2025, 5, 1),
                payment_date=date(2025, 5, 15),
            ),
        ]
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        brapi_symbols = [c.args[0] for c in brapi_provider.get_dividends.call_args_list]
        yf_symbols = [c.args[0] for c in yfinance_provider.get_dividends.call_args_list]

        # BR stocks + FIIs route through Brapi first
        assert set(brapi_symbols) == {"PETR4.SA", "HGLG11.SA"}
        # US tickers go straight to yfinance
        assert "AAPL" in yf_symbols
        # Crypto excluded
        assert "BTC" not in brapi_symbols + yf_symbols

    def test_br_falls_back_to_yfinance_when_brapi_unavailable(self, scheduler, brapi_provider, yfinance_provider, dados_provider, db):
        _setup_holdings(db)

        brapi_provider.get_dividends.side_effect = BrapiFeatureUnavailable("plan")
        yfinance_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=Decimal("0.50"),
                record_date=date(2025, 6, 1), ex_date=date(2025, 6, 1),
                payment_date=None,
            ),
        ]
        dados_provider.scrape_dividends.return_value = []

        scheduler.scrape_all(db)

        yf_symbols = [c.args[0] for c in yfinance_provider.get_dividends.call_args_list]
        # BR symbols hit yfinance with .SA preserved
        assert "PETR4.SA" in yf_symbols
        assert "HGLG11.SA" in yf_symbols

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1
        assert records[0].currency == "BRL"

    def test_stores_us_dividends(self, scheduler, brapi_provider, yfinance_provider, db):
        _setup_holdings(db)

        brapi_provider.get_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=Decimal("0.25"),
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
        assert records[0].currency == "USD"

    def test_stores_br_dividends_from_brapi(self, scheduler, brapi_provider, yfinance_provider, db):
        _setup_holdings(db)

        brapi_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividendo", value=Decimal("1.50"),
                record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
                payment_date=date(2025, 11, 28),
            ),
        ]
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1
        assert records[0].currency == "BRL"
        assert records[0].payment_date == date(2025, 11, 28)

    def test_skips_existing_duplicates(self, scheduler, brapi_provider, yfinance_provider, db):
        _setup_holdings(db)

        db.add(DividendHistory(
            symbol="AAPL", dividend_type="Dividend", value=0.25,
            record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
            payment_date=None,
        ))
        db.commit()

        brapi_provider.get_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=Decimal("0.25"),
                record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
                payment_date=None,
            ),
        ]

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="AAPL").all()
        assert len(records) == 1
