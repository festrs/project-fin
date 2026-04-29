"""Portfolio recompute determinism: known holdings → exact Decimal output."""

from datetime import date
from decimal import Decimal

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.models.user import User
from app.money import Currency
from app.services.portfolio import PortfolioService


def _create_user(db) -> User:
    user = User(name="Det User", email="det@example.com", password_hash="x")
    db.add(user)
    db.flush()
    return user


def test_deterministic_quantity_and_avg_price(db):
    """Buy 100 shares @ $150 → quantity=100, avg=$150, total_cost=$15000."""
    user = _create_user(db)
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=Decimal("60"), country="US", type="stock")
    db.add(ac)
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
        type="buy", quantity=Decimal("100"), unit_price=Decimal("150.00"),
        total_value=Decimal("15000.00"), currency="USD", date=date(2025, 1, 1),
    ))
    db.commit()

    service = PortfolioService(db)
    holdings = service.get_holdings(user.id)
    assert len(holdings) == 1
    h = holdings[0]
    assert h["quantity"] == Decimal("100")
    assert h["avg_price"].amount == Decimal("150")
    assert h["avg_price"].currency == Currency.USD
    assert h["total_cost"].amount == Decimal("15000")
    assert h["total_cost"].currency == Currency.USD


def test_deterministic_partial_sell(db):
    """Buy 200 @ $60, sell 50 → quantity=150, avg=$60, total_cost=$9000."""
    user = _create_user(db)
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=Decimal("100"), country="US", type="stock")
    db.add(ac)
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="MSFT",
        type="buy", quantity=Decimal("200"), unit_price=Decimal("60"),
        total_value=Decimal("12000"), currency="USD", date=date(2025, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="MSFT",
        type="sell", quantity=Decimal("50"), unit_price=Decimal("70"),
        total_value=Decimal("3500"), currency="USD", date=date(2025, 3, 1),
    ))
    db.commit()

    service = PortfolioService(db)
    holdings = service.get_holdings(user.id)
    h = next(x for x in holdings if x["symbol"] == "MSFT")
    assert h["quantity"] == Decimal("150")
    assert h["avg_price"].amount == Decimal("60")
    assert h["total_cost"].amount == Decimal("9000")


def test_fully_sold_holding_excluded(db):
    """Buy 100, sell 100 → holding excluded from results."""
    user = _create_user(db)
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=Decimal("100"), country="US", type="stock")
    db.add(ac)
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="GOOGL",
        type="buy", quantity=Decimal("100"), unit_price=Decimal("100"),
        total_value=Decimal("10000"), currency="USD", date=date(2025, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="GOOGL",
        type="sell", quantity=Decimal("100"), unit_price=Decimal("120"),
        total_value=Decimal("12000"), currency="USD", date=date(2025, 3, 1),
    ))
    db.commit()

    service = PortfolioService(db)
    holdings = service.get_holdings(user.id)
    assert all(h["symbol"] != "GOOGL" for h in holdings)


def test_multiple_buys_accumulate(db):
    """Two buys: 100 @ $100, 100 @ $200 → 200 shares, avg $150, cost $30000."""
    user = _create_user(db)
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=Decimal("100"), country="US", type="stock")
    db.add(ac)
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="AMZN",
        type="buy", quantity=Decimal("100"), unit_price=Decimal("100"),
        total_value=Decimal("10000"), currency="USD", date=date(2025, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="AMZN",
        type="buy", quantity=Decimal("100"), unit_price=Decimal("200"),
        total_value=Decimal("20000"), currency="USD", date=date(2025, 2, 1),
    ))
    db.commit()

    service = PortfolioService(db)
    holdings = service.get_holdings(user.id)
    h = next(x for x in holdings if x["symbol"] == "AMZN")
    assert h["quantity"] == Decimal("200")
    assert h["avg_price"].amount == Decimal("150")
    assert h["total_cost"].amount == Decimal("30000")
