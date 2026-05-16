"""Regression tests for the BR-yield override on /api/mobile/quotes.

The mobile endpoint must always serve a yield computed from `dividend_history`
records when records exist, regardless of what the upstream provider
(yfinance/Brapi) returns — those are broken for B3 stocks (ITUB3 = 0.53%
vs real ~7.7%).
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from app.models.dividend_history import DividendHistory
from app.money import Currency, Money

HEADERS = {"X-API-Key": "test-mobile-key"}


def _seed_dividends(db, symbol: str, monthly_per_share: Decimal, months: int = 12):
    today = date.today()
    for offset in range(1, months + 1):
        db.add(DividendHistory(
            symbol=symbol, dividend_type="JCP", value=monthly_per_share,
            record_date=today - timedelta(days=30 * offset),
            ex_date=today - timedelta(days=30 * offset),
            payment_date=today - timedelta(days=30 * offset - 5),
            currency="BRL",
        ))
    db.commit()


def _stub_market_data(monkeypatch, *, br_yield: Decimal, price: Decimal):
    """Patch MarketDataService.get_stock_quote so the test doesn't depend on
    live yfinance / Status Invest. The stub returns a deliberately broken
    yield (mimicking yfinance for B3) so we can prove the override fires.
    """
    from app.services import market_data as mod

    def fake_get_stock_quote(self, symbol, country="US", db=None, db_only=False):
        return {
            "symbol": symbol, "name": symbol,
            "current_price": Money(price, Currency.BRL),
            "currency": Currency.BRL,
            "market_cap": Money(Decimal("0"), Currency.BRL),
            "dividend_yield": br_yield,
        }
    monkeypatch.setattr(mod.MarketDataService, "get_stock_quote", fake_get_stock_quote)


class TestBRYieldOverride:
    def test_br_yield_overridden_by_records(self, client, db, monkeypatch):
        _seed_dividends(db, "ITUB3.SA", monthly_per_share=Decimal("0.25"))
        _stub_market_data(monkeypatch, br_yield=Decimal("0.53"), price=Decimal("50"))

        resp = client.get("/api/mobile/quotes",
                          params={"symbols": "ITUB3.SA"}, headers=HEADERS)
        assert resp.status_code == 200
        quote = resp.json()["quotes"][0]
        # 12 × 0.25 = 3 / 50 × 100 = 6.00 (overrides the broken 0.53)
        assert quote["dividend_yield"] == "6.00"

    def test_br_yield_falls_through_when_no_records(self, client, db, monkeypatch):
        # New BR ticker with no recorded dividends — the upstream value stays.
        _stub_market_data(monkeypatch, br_yield=Decimal("3.5"), price=Decimal("10"))

        resp = client.get("/api/mobile/quotes",
                          params={"symbols": "NEWIPO.SA"}, headers=HEADERS)
        assert resp.status_code == 200
        quote = resp.json()["quotes"][0]
        assert quote["dividend_yield"] == "3.5"

    def test_us_yield_not_overridden(self, client, db, monkeypatch):
        # Even with BR-shaped records mistakenly added, US tickers are not
        # touched — yfinance is reliable for US dividend yields.
        _seed_dividends(db, "AAPL", monthly_per_share=Decimal("99"))
        _stub_market_data(monkeypatch, br_yield=Decimal("0.4"), price=Decimal("200"))

        resp = client.get("/api/mobile/quotes",
                          params={"symbols": "AAPL"}, headers=HEADERS)
        assert resp.status_code == 200
        quote = resp.json()["quotes"][0]
        assert quote["dividend_yield"] == "0.4"
