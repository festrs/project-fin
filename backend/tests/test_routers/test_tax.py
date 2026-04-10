from datetime import date
from decimal import Decimal

from app.models.asset_class import AssetClass
from app.models.transaction import Transaction


def _setup_data(db, user_id):
    ac = AssetClass(
        user_id=user_id,
        name="BR Stocks",
        country="BR",
        type="stock",
        target_weight=100.0,
    )
    db.add(ac)
    db.commit()
    db.refresh(ac)

    tx1 = Transaction(
        user_id=user_id,
        asset_class_id=ac.id,
        asset_symbol="PETR4",
        type="buy",
        quantity=1000,
        unit_price=Decimal("30.0"),
        total_value=Decimal("30000.0"),
        currency="BRL",
        date=date(2026, 1, 10),
    )
    tx2 = Transaction(
        user_id=user_id,
        asset_class_id=ac.id,
        asset_symbol="PETR4",
        type="sell",
        quantity=700,
        unit_price=Decimal("35.0"),
        total_value=Decimal("24500.0"),
        currency="BRL",
        date=date(2026, 3, 15),
    )
    db.add_all([tx1, tx2])
    db.commit()


class TestTaxRouter:
    def test_get_report(self, client, db, default_user, auth_headers):
        _setup_data(db, default_user.id)
        resp = client.get("/api/tax/report?year=2026", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
        mar = next(m for m in data if m["month"] == 3)
        assert mar["stocks"]["exempt"] is False
        assert float(mar["total_tax_due"]) > 0

    def test_get_report_default_year(self, client, db, default_user, auth_headers):
        resp = client.get("/api/tax/report", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 12

    def test_empty_report(self, client, db, default_user, auth_headers):
        resp = client.get("/api/tax/report?year=2025", headers=auth_headers)
        assert resp.status_code == 200
        for month in resp.json():
            assert float(month["total_tax_due"]) == 0
