from datetime import date
from decimal import Decimal

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction


def test_create_buy_transaction(db):
    user = User(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="Stocks")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    tx = Transaction(
        user_id=user.id,
        asset_class_id=ac.id,
        asset_symbol="AAPL",
        type="buy",
        quantity=10.0,
        unit_price=Decimal("150.0"),
        total_value=Decimal("1500.0"),
        currency="USD",
        date=date(2025, 1, 15),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    assert tx.id is not None
    assert len(tx.id) == 36
    assert tx.type == "buy"
    assert tx.quantity == 10.0
    assert tx.unit_price == Decimal("150.0")
    assert tx.total_value == Decimal("1500.0")
    assert tx.currency == "USD"
    assert tx.tax_amount is None
    assert tx.notes is None
    assert tx.created_at is not None
    assert tx.updated_at is not None


def test_create_dividend_transaction(db):
    user = User(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="Stocks")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    tx = Transaction(
        user_id=user.id,
        asset_class_id=ac.id,
        asset_symbol="AAPL",
        type="dividend",
        quantity=0.0,
        unit_price=Decimal("0.0"),
        total_value=Decimal("25.50"),
        currency="USD",
        date=date(2025, 3, 1),
        notes="Q1 dividend",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    assert tx.type == "dividend"
    assert tx.quantity == 0.0
    assert tx.unit_price == Decimal("0.0")
    assert tx.total_value == Decimal("25.50")
    assert tx.notes == "Q1 dividend"


def test_filter_by_type(db):
    user = User(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="Stocks")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    tx1 = Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
        type="buy", quantity=10, unit_price=Decimal("150"), total_value=Decimal("1500"),
        currency="USD", date=date(2025, 1, 1),
    )
    tx2 = Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
        type="sell", quantity=5, unit_price=Decimal("160"), total_value=Decimal("800"),
        currency="USD", date=date(2025, 2, 1),
    )
    tx3 = Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
        type="buy", quantity=3, unit_price=Decimal("155"), total_value=Decimal("465"),
        currency="USD", date=date(2025, 3, 1),
    )
    db.add_all([tx1, tx2, tx3])
    db.commit()

    buys = db.query(Transaction).filter(Transaction.type == "buy").all()
    assert len(buys) == 2

    sells = db.query(Transaction).filter(Transaction.type == "sell").all()
    assert len(sells) == 1
