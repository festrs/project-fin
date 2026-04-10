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
