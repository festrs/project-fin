"""Routing tests for the simplified DividendScheduler.

After the StatusInvest cutover the scheduler has exactly one provider per
market: Status Invest for BR (.SA), yfinance for US. No fallbacks, no dedup
across providers — each ticker hits one source.

These tests assert that contract end-to-end:
  - BR symbols call StatusInvest once and yfinance zero times.
  - US symbols call yfinance once and StatusInvest zero times.
  - Brapi has been fully removed from the import surface.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.models.user import User
from app.providers.common import DividendRecord
from app.services.auth import hash_password
from app.services.dividend_scraper_scheduler import DividendScheduler


@pytest.fixture
def statusinvest_provider():
    return MagicMock()


@pytest.fixture
def yfinance_provider():
    return MagicMock()


@pytest.fixture
def scheduler(statusinvest_provider, yfinance_provider):
    return DividendScheduler(
        statusinvest_provider=statusinvest_provider,
        yfinance_provider=yfinance_provider,
        br_delay=0.0,
        us_delay=0.0,
    )


def _seed_one_br_one_us(db):
    user = User(name="Test", email="t@t.com", password_hash=hash_password("pw"))
    db.add(user); db.flush()

    ac_br = AssetClass(user_id=user.id, name="BR", target_weight=50.0, country="BR")
    ac_us = AssetClass(user_id=user.id, name="US", target_weight=50.0, country="US")
    db.add_all([ac_br, ac_us]); db.flush()

    db.add_all([
        Transaction(
            user_id=user.id, asset_class_id=ac_br.id, asset_symbol="ITUB3.SA",
            type="buy", quantity=100, unit_price=40.0, total_value=4000.0,
            currency="BRL", date=date(2025, 1, 1),
        ),
        Transaction(
            user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
            type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
            currency="USD", date=date(2025, 1, 1),
        ),
    ])
    db.commit()


class TestDividendSchedulerRouting:
    def test_br_symbols_route_to_status_invest_only(
        self, scheduler, statusinvest_provider, yfinance_provider, db
    ):
        _seed_one_br_one_us(db)
        statusinvest_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="JCP", value=Decimal("0.0182"),
                record_date=date(2026, 3, 31), ex_date=date(2026, 3, 31),
                payment_date=date(2026, 5, 4),
            ),
        ]
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        si_calls = [c.args[0] for c in statusinvest_provider.get_dividends.call_args_list]
        yf_calls = [c.args[0] for c in yfinance_provider.get_dividends.call_args_list]
        assert "ITUB3.SA" in si_calls
        assert "ITUB3.SA" not in yf_calls
        assert "ITUB3" not in yf_calls  # not even the bare form

    def test_us_symbols_route_to_yfinance_only(
        self, scheduler, statusinvest_provider, yfinance_provider, db
    ):
        _seed_one_br_one_us(db)
        statusinvest_provider.get_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        si_calls = [c.args[0] for c in statusinvest_provider.get_dividends.call_args_list]
        yf_calls = [c.args[0] for c in yfinance_provider.get_dividends.call_args_list]
        assert "AAPL" in yf_calls
        assert "AAPL" not in si_calls

    def test_dividend_scheduler_does_not_import_brapi_or_dados(self):
        """The scheduler module must not depend on Brapi or DadosDeMercado.

        These providers still live in the repo for other features (split
        detection, fundamentals API), but the dividend pipeline is the one
        place that must be a single source of truth — Status Invest only.
        """
        import app.services.dividend_scraper_scheduler as sched
        source = open(sched.__file__).read()
        assert "from app.providers.brapi" not in source
        assert "from app.providers.dados_de_mercado" not in source
        assert "BrapiProvider" not in source
        assert "DadosDeMercadoProvider" not in source

    def test_scheduler_constructor_only_takes_two_providers(
        self, statusinvest_provider, yfinance_provider
    ):
        """No legacy kwargs (`brapi_provider`, `dados_provider`) must remain."""
        with pytest.raises(TypeError):
            DividendScheduler(
                statusinvest_provider=statusinvest_provider,
                yfinance_provider=yfinance_provider,
                brapi_provider=MagicMock(),  # legacy kwarg — should fail
            )
