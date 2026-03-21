from datetime import date

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.services.auth import create_access_token


def _setup_split(db, user):
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US", type="stock")
    db.add(ac)
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
        type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
        currency="USD", date=date(2025, 1, 1),
    ))

    split = StockSplit(
        user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
        from_factor=1, to_factor=2, status="pending", asset_class_id=ac.id,
    )
    db.add(split)
    db.commit()
    return split


class TestSplitsRouter:
    def test_get_pending(self, client, default_user, db):
        split = _setup_split(db, default_user)
        token = create_access_token(default_user.id)
        resp = client.get("/api/splits/pending", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "FAST"
        assert data[0]["current_quantity"] == 100
        assert data[0]["new_quantity"] == 200

    def test_apply_split(self, client, default_user, db):
        split = _setup_split(db, default_user)
        token = create_access_token(default_user.id)
        resp = client.post(f"/api/splits/{split.id}/apply", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        db.refresh(split)
        assert split.status == "applied"
        assert split.resolved_at is not None

    def test_dismiss_split(self, client, default_user, db):
        split = _setup_split(db, default_user)
        token = create_access_token(default_user.id)
        resp = client.post(f"/api/splits/{split.id}/dismiss", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        db.refresh(split)
        assert split.status == "dismissed"

    def test_apply_already_applied(self, client, default_user, db):
        split = _setup_split(db, default_user)
        token = create_access_token(default_user.id)
        client.post(f"/api/splits/{split.id}/apply", headers={"Authorization": f"Bearer {token}"})
        resp = client.post(f"/api/splits/{split.id}/apply", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400

    def test_apply_nonexistent(self, client, default_user, db):
        token = create_access_token(default_user.id)
        resp = client.post("/api/splits/nonexistent/apply", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_no_pending_returns_empty(self, client, default_user, db):
        token = create_access_token(default_user.id)
        resp = client.get("/api/splits/pending", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []
