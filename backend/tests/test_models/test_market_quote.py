from datetime import datetime, timezone

from app.models.market_quote import MarketQuote


def test_market_quote_has_correct_columns():
    quote = MarketQuote(
        symbol="AAPL",
        name="Apple Inc",
        current_price=175.50,
        currency="USD",
        market_cap=2_800_000_000_000,
        country="US",
    )
    assert quote.symbol == "AAPL"
    assert quote.name == "Apple Inc"
    assert quote.current_price == 175.50
    assert quote.currency == "USD"
    assert quote.market_cap == 2_800_000_000_000
    assert quote.country == "US"


def test_market_quote_persists(db):
    quote = MarketQuote(
        symbol="PETR4.SA",
        name="Petrobras",
        current_price=38.50,
        currency="BRL",
        market_cap=500_000_000_000,
        country="BR",
    )
    db.add(quote)
    db.commit()

    loaded = db.query(MarketQuote).filter_by(symbol="PETR4.SA").first()
    assert loaded is not None
    assert loaded.current_price == 38.50
    assert loaded.country == "BR"
    assert loaded.updated_at is not None
