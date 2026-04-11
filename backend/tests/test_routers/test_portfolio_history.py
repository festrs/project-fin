from datetime import date, timedelta
from decimal import Decimal

from app.models.portfolio_snapshot import PortfolioSnapshot


def _create_snapshots(db, user_id: str, count: int):
    """Create `count` daily snapshots ending yesterday."""
    today = date.today()
    for i in range(count):
        d = today - timedelta(days=count - i)
        snap = PortfolioSnapshot(
            user_id=user_id,
            date=d,
            total_value_brl=Decimal("1000.00") + Decimal(str(i)),
        )
        db.add(snap)
    db.commit()


def test_history_1w(client, db, default_user, auth_headers):
    _create_snapshots(db, default_user.id, 30)
    resp = client.get("/api/portfolio/history?period=1W", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 7


def test_history_1m(client, db, default_user, auth_headers):
    _create_snapshots(db, default_user.id, 60)
    resp = client.get("/api/portfolio/history?period=1M", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 30


def test_history_all(client, db, default_user, auth_headers):
    _create_snapshots(db, default_user.id, 60)
    resp = client.get("/api/portfolio/history?period=ALL", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 60


def test_history_empty(client, db, default_user, auth_headers):
    resp = client.get("/api/portfolio/history?period=1M", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


def test_latest_snapshot(client, db, default_user, auth_headers):
    yesterday = date.today() - timedelta(days=1)
    snap = PortfolioSnapshot(
        user_id=default_user.id,
        date=yesterday,
        total_value_brl=Decimal("5000.00"),
    )
    db.add(snap)
    db.commit()
    resp = client.get("/api/portfolio/snapshot/latest", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["date"] == yesterday.isoformat()
    assert data["total_value_brl"] == "5000.00000000"


def test_latest_snapshot_empty(client, db, default_user, auth_headers):
    resp = client.get("/api/portfolio/snapshot/latest", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None
