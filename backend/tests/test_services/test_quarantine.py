from datetime import date, timedelta

import pytest

from app.models import User, AssetClass, Transaction, QuarantineConfig
from app.services.quarantine import QuarantineService


def _create_user(db, name="Test User", email="test@example.com"):
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_asset_class(db, user_id, name="Stocks", target_weight=60.0):
    ac = AssetClass(user_id=user_id, name=name, target_weight=target_weight)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _create_buy(db, user_id, asset_class_id, symbol, buy_date, quantity=1.0, unit_price=100.0):
    tx = Transaction(
        user_id=user_id,
        asset_class_id=asset_class_id,
        asset_symbol=symbol,
        type="buy",
        quantity=quantity,
        unit_price=unit_price,
        total_value=quantity * unit_price,
        currency="USD",
        date=buy_date,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


class TestQuarantineService:
    def test_not_quarantined_with_one_buy(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id)
        _create_buy(db, user.id, ac.id, "AAPL", date.today() - timedelta(days=10))

        svc = QuarantineService(db)
        status = svc.get_asset_status(user.id, "AAPL")

        assert status.asset_symbol == "AAPL"
        assert status.buy_count_in_period == 1
        assert status.is_quarantined is False
        assert status.quarantine_ends_at is None

    def test_quarantined_with_two_buys(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id)
        _create_buy(db, user.id, ac.id, "AAPL", date.today() - timedelta(days=30))
        _create_buy(db, user.id, ac.id, "AAPL", date.today() - timedelta(days=10))

        svc = QuarantineService(db)
        status = svc.get_asset_status(user.id, "AAPL")

        assert status.buy_count_in_period == 2
        assert status.is_quarantined is True
        # quarantine_ends_at = date of 2nd buy + period_days (180 default)
        expected_end = date.today() - timedelta(days=10) + timedelta(days=180)
        assert status.quarantine_ends_at == expected_end

    def test_not_quarantined_if_buys_outside_period(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id)
        # Both buys are outside the 180-day window
        _create_buy(db, user.id, ac.id, "AAPL", date.today() - timedelta(days=200))
        _create_buy(db, user.id, ac.id, "AAPL", date.today() - timedelta(days=190))

        svc = QuarantineService(db)
        status = svc.get_asset_status(user.id, "AAPL")

        assert status.buy_count_in_period == 0
        assert status.is_quarantined is False
        assert status.quarantine_ends_at is None

    def test_get_all_quarantine_statuses(self, db):
        user = _create_user(db)
        ac = _create_asset_class(db, user.id)
        _create_buy(db, user.id, ac.id, "AAPL", date.today() - timedelta(days=10))
        _create_buy(db, user.id, ac.id, "AAPL", date.today() - timedelta(days=5))
        _create_buy(db, user.id, ac.id, "GOOG", date.today() - timedelta(days=3))

        svc = QuarantineService(db)
        statuses = svc.get_all_statuses(user.id)

        symbols = {s.asset_symbol for s in statuses}
        assert symbols == {"AAPL", "GOOG"}

        aapl = next(s for s in statuses if s.asset_symbol == "AAPL")
        assert aapl.is_quarantined is True

        goog = next(s for s in statuses if s.asset_symbol == "GOOG")
        assert goog.is_quarantined is False
