from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction
from app.models.user import User
from app.providers.dados_de_mercado import DividendRecord
from app.services.dividend_scraper_scheduler import DividendScraperScheduler


@pytest.fixture
def provider():
    return MagicMock()


@pytest.fixture
def scheduler(provider):
    return DividendScraperScheduler(provider=provider, delay=0.0)


def _setup_br_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR")
    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US")
    db.add_all([ac_br, ac_us])
    db.flush()

    tx_br1 = Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
        type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
        currency="BRL", date=date(2025, 1, 1),
    )
    tx_br2 = Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="VALE3.SA",
        type="buy", quantity=50, unit_price=60.0, total_value=3000.0,
        currency="BRL", date=date(2025, 1, 1),
    )
    tx_us = Transaction(
        user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
        type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
        currency="USD", date=date(2025, 1, 1),
    )
    db.add_all([tx_br1, tx_br2, tx_us])
    db.commit()


class TestDividendScraperScheduler:
    def test_scrapes_only_br_symbols(self, scheduler, provider, db):
        _setup_br_holdings(db)

        provider.scrape_dividends.return_value = []

        scheduler.scrape_all(db)

        scraped_symbols = [call.args[0] for call in provider.scrape_dividends.call_args_list]
        assert "AAPL" not in scraped_symbols
        assert set(scraped_symbols) == {"PETR4.SA", "VALE3.SA"}

    def test_stores_scraped_dividends(self, scheduler, provider, db):
        _setup_br_holdings(db)

        provider.scrape_dividends.side_effect = lambda sym: [
            DividendRecord(
                dividend_type="Dividendo", value=1.50,
                record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
                payment_date=date(2025, 11, 28),
            ),
        ] if sym == "PETR4.SA" else []

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1
        assert records[0].value == 1.50
        assert records[0].dividend_type == "Dividendo"

    def test_skips_existing_duplicates(self, scheduler, provider, db):
        _setup_br_holdings(db)

        existing = DividendHistory(
            symbol="PETR4.SA", dividend_type="Dividendo", value=1.50,
            record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
            payment_date=date(2025, 11, 28),
        )
        db.add(existing)
        db.commit()

        provider.scrape_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividendo", value=1.50,
                record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
                payment_date=date(2025, 11, 28),
            ),
        ]

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1

    def test_continues_on_individual_failure(self, scheduler, provider, db):
        _setup_br_holdings(db)

        def side_effect(sym):
            if sym == "PETR4.SA":
                raise Exception("Network error")
            return [
                DividendRecord(
                    dividend_type="Dividendo", value=2.00,
                    record_date=date(2025, 5, 10), ex_date=date(2025, 5, 11),
                    payment_date=date(2025, 6, 1),
                ),
            ]

        provider.scrape_dividends.side_effect = side_effect

        scheduler.scrape_all(db)

        petr = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(petr) == 0

        vale = db.query(DividendHistory).filter_by(symbol="VALE3.SA").all()
        assert len(vale) == 1
