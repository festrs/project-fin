from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User


def _create_user(db):
    user = User(name="Test", email="snap@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_portfolio_snapshot(db):
    user = _create_user(db)
    snapshot = PortfolioSnapshot(
        user_id=user.id,
        date=date(2026, 4, 10),
        total_value_brl=Decimal("12345.67890000"),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    assert snapshot.id is not None
    assert snapshot.user_id == user.id
    assert snapshot.date == date(2026, 4, 10)
    assert snapshot.total_value_brl == Decimal("12345.67890000")
    assert snapshot.created_at is not None


def test_unique_constraint_user_date(db):
    user = _create_user(db)
    snap1 = PortfolioSnapshot(
        user_id=user.id,
        date=date(2026, 4, 10),
        total_value_brl=Decimal("100.00"),
    )
    db.add(snap1)
    db.commit()

    snap2 = PortfolioSnapshot(
        user_id=user.id,
        date=date(2026, 4, 10),
        total_value_brl=Decimal("200.00"),
    )
    db.add(snap2)
    with pytest.raises(IntegrityError):
        db.commit()


def test_different_dates_same_user_allowed(db):
    user = _create_user(db)
    snap1 = PortfolioSnapshot(
        user_id=user.id,
        date=date(2026, 4, 10),
        total_value_brl=Decimal("100.00"),
    )
    snap2 = PortfolioSnapshot(
        user_id=user.id,
        date=date(2026, 4, 11),
        total_value_brl=Decimal("200.00"),
    )
    db.add_all([snap1, snap2])
    db.commit()

    assert snap1.id != snap2.id


# ---------- Snapshot Scheduler Tests ----------

from unittest.mock import patch, MagicMock

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.money import Money, Currency
from app.services.snapshot_scheduler import SnapshotScheduler


def _setup_user_with_holdings(db):
    """Create a user with an asset class, asset weight, and a buy transaction."""
    user = User(name="Snap User", email="snapscheduler@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="US Stocks", country="US", target_weight=100.0)
    db.add(ac)
    db.commit()
    db.refresh(ac)

    aw = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=100.0)
    db.add(aw)
    db.commit()

    tx = Transaction(
        user_id=user.id,
        asset_symbol="AAPL",
        asset_class_id=ac.id,
        type="buy",
        quantity=Decimal("10"),
        unit_price=Decimal("150.00"),
        total_value=Decimal("1500.00"),
        currency="USD",
        date=date(2026, 1, 1),
    )
    db.add(tx)
    db.commit()

    return user


@patch("app.services.snapshot_scheduler.fetch_exchange_rate", return_value=5.0)
@patch("app.services.snapshot_scheduler.get_market_data_service")
def test_creates_snapshot_for_user(mock_market_data_svc, mock_fx, db):
    user = _setup_user_with_holdings(db)

    # Mock market data service so enrich_holdings gets a price
    mock_service = MagicMock()
    mock_service.get_quote_safe.return_value = Money(Decimal("200.00"), Currency.USD)
    mock_market_data_svc.return_value = mock_service

    scheduler = SnapshotScheduler()
    scheduler.take_snapshots(db)

    snapshot = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.user_id == user.id)
        .first()
    )
    assert snapshot is not None
    assert snapshot.date == date.today()
    # 10 shares * $200 = $2000 USD * 5.0 exchange rate = R$ 10,000
    assert snapshot.total_value_brl == Decimal("10000.00") * Decimal("1")


@patch("app.services.snapshot_scheduler.fetch_exchange_rate", return_value=5.0)
@patch("app.services.snapshot_scheduler.get_market_data_service")
def test_skips_if_already_exists(mock_market_data_svc, mock_fx, db):
    user = _setup_user_with_holdings(db)

    # Create an existing snapshot for today
    existing = PortfolioSnapshot(
        user_id=user.id,
        date=date.today(),
        total_value_brl=Decimal("999.00"),
    )
    db.add(existing)
    db.commit()

    mock_service = MagicMock()
    mock_service.get_quote_safe.return_value = Money(Decimal("200.00"), Currency.USD)
    mock_market_data_svc.return_value = mock_service

    scheduler = SnapshotScheduler()
    scheduler.take_snapshots(db)

    # Should still be only one snapshot with the original value
    snapshots = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.user_id == user.id)
        .all()
    )
    assert len(snapshots) == 1
    assert snapshots[0].total_value_brl == Decimal("999.00")
