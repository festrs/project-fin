from datetime import datetime, timezone
from decimal import Decimal

from app.models.market_quote import MarketQuote


def test_market_quote_has_correct_columns():
    quote = MarketQuote(
        symbol="AAPL",
        name="Apple Inc",
        current_price=Decimal("175.50"),
        currency="USD",
        market_cap=Decimal("2800000000000"),
        country="US",
    )
    assert quote.symbol == "AAPL"
    assert quote.name == "Apple Inc"
    assert quote.current_price == Decimal("175.50")
    assert quote.currency == "USD"
    assert quote.market_cap == Decimal("2800000000000")
    assert quote.country == "US"


def test_market_quote_persists(db):
    quote = MarketQuote(
        symbol="PETR4.SA",
        name="Petrobras",
        current_price=Decimal("38.50"),
        currency="BRL",
        market_cap=Decimal("500000000000"),
        country="BR",
    )
    db.add(quote)
    db.commit()

    loaded = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
    assert loaded is not None
    assert loaded.current_price == Decimal("38.50")
    assert loaded.country == "BR"
    assert loaded.updated_at is not None
