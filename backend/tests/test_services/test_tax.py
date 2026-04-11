from datetime import date
from decimal import Decimal

import pytest

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.services.tax import TaxService


def _create_user(db):
    user = User(name="Tax Test", email="tax@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_class(db, user_id, name="BR Stocks"):
    ac = AssetClass(user_id=user_id, name=name, country="BR", type="stock", target_weight=50.0)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _add_tx(db, user_id, ac_id, symbol, tx_type, qty, unit_price, total, tx_date, tax=None):
    tx = Transaction(
        user_id=user_id,
        asset_class_id=ac_id,
        asset_symbol=symbol,
        type=tx_type,
        quantity=qty,
        unit_price=Decimal(str(unit_price)),
        total_value=Decimal(str(total)),
        currency="BRL",
        date=tx_date,
        tax_amount=Decimal(str(tax)) if tax else None,
    )
    db.add(tx)
    db.commit()
    return tx


class TestTaxService:
    def test_no_sells_returns_empty(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)
        _add_tx(db, user.id, ac.id, "PETR4", "buy", 100, 30.00, 3000.00, date(2026, 1, 15))

        service = TaxService(db)
        report = service.get_monthly_report(user.id, 2026)

        assert len(report) == 12
        for month_data in report:
            assert month_data["stocks"]["total_sales"] == "0"
            assert month_data["stocks"]["total_gain"] == "0"
            assert month_data["stocks"]["tax_due"] == "0"
            assert month_data["fiis"]["total_sales"] == "0"
            assert month_data["fiis"]["tax_due"] == "0"
            assert month_data["total_tax_due"] == "0"

    def test_stock_exempt_under_20k(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)

        # Buy 100 shares at R$30
        _add_tx(db, user.id, ac.id, "PETR4", "buy", 100, 30.00, 3000.00, date(2026, 1, 10))
        # Sell 100 shares at R$50 (total = R$5,000, gain = R$2,000) -- under 20k
        _add_tx(db, user.id, ac.id, "PETR4", "sell", 100, 50.00, 5000.00, date(2026, 2, 15))

        service = TaxService(db)
        report = service.get_monthly_report(user.id, 2026)

        feb = report[1]  # month 2
        assert feb["stocks"]["exempt"] is True
        assert Decimal(feb["stocks"]["total_gain"]) == Decimal("2000.00000000")
        assert Decimal(feb["stocks"]["tax_due"]) == Decimal("0")
        assert Decimal(feb["total_tax_due"]) == Decimal("0")

    def test_stock_taxed_over_20k(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)

        # Buy 1000 shares at R$20
        _add_tx(db, user.id, ac.id, "VALE3", "buy", 1000, 20.00, 20000.00, date(2026, 1, 5))
        # Sell 1000 shares at R$25 (total = R$25,000 >= 20k, gain = R$5,000)
        _add_tx(db, user.id, ac.id, "VALE3", "sell", 1000, 25.00, 25000.00, date(2026, 3, 10))

        service = TaxService(db)
        report = service.get_monthly_report(user.id, 2026)

        mar = report[2]  # month 3
        assert mar["stocks"]["exempt"] is False
        assert Decimal(mar["stocks"]["total_sales"]) == Decimal("25000.00000000")
        assert Decimal(mar["stocks"]["total_gain"]) == Decimal("5000.00000000")
        # 15% of 5000 = 750
        assert Decimal(mar["stocks"]["tax_due"]) == Decimal("750.00")
        assert Decimal(mar["total_tax_due"]) == Decimal("750.00")

    def test_fii_always_taxed(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id, name="FIIs")

        # Buy 50 FII shares at R$100
        _add_tx(db, user.id, ac.id, "HGLG11", "buy", 50, 100.00, 5000.00, date(2026, 2, 1))
        # Sell 50 at R$120 (total = R$6,000, gain = R$1,000) -- under 20k but FII always taxed
        _add_tx(db, user.id, ac.id, "HGLG11", "sell", 50, 120.00, 6000.00, date(2026, 4, 20))

        service = TaxService(db)
        report = service.get_monthly_report(user.id, 2026)

        apr = report[3]  # month 4
        assert Decimal(apr["fiis"]["total_sales"]) == Decimal("6000.00000000")
        assert Decimal(apr["fiis"]["total_gain"]) == Decimal("1000.00000000")
        # 20% of 1000 = 200
        assert Decimal(apr["fiis"]["tax_due"]) == Decimal("200.00")
        assert Decimal(apr["total_tax_due"]) == Decimal("200.00")

    def test_loss_no_tax(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)

        # Buy 200 shares at R$50
        _add_tx(db, user.id, ac.id, "ITUB4", "buy", 200, 50.00, 10000.00, date(2026, 1, 5))
        # Sell 200 at R$40 (total = R$8,000, loss = -R$2,000)
        _add_tx(db, user.id, ac.id, "ITUB4", "sell", 200, 40.00, 8000.00, date(2026, 5, 10))

        service = TaxService(db)
        report = service.get_monthly_report(user.id, 2026)

        may = report[4]  # month 5
        assert Decimal(may["stocks"]["total_gain"]) < Decimal("0")
        assert Decimal(may["stocks"]["tax_due"]) == Decimal("0")
        assert Decimal(may["total_tax_due"]) == Decimal("0")

    def test_irrf_deducted(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)

        # Buy 1000 shares at R$20
        _add_tx(db, user.id, ac.id, "BBDC4", "buy", 1000, 20.00, 20000.00, date(2026, 1, 3))
        # Sell 1000 at R$30 (total = R$30,000, gain = R$10,000), IRRF = R$500
        _add_tx(db, user.id, ac.id, "BBDC4", "sell", 1000, 30.00, 30000.00, date(2026, 6, 15), tax=500.00)

        service = TaxService(db)
        report = service.get_monthly_report(user.id, 2026)

        jun = report[5]  # month 6
        assert jun["stocks"]["exempt"] is False
        # 15% of 10,000 = 1,500 - 500 IRRF = 1,000
        assert Decimal(jun["stocks"]["tax_due"]) == Decimal("1000.00")
        assert Decimal(jun["total_tax_due"]) == Decimal("1000.00")

    def test_avg_cost_from_prior_year(self, db):
        """Avg cost computed from prior year buys should be accurate."""
        user = _create_user(db)
        ac = _create_class(db, user.id)

        # Buy in 2025
        _add_tx(db, user.id, ac.id, "WEGE3", "buy", 500, 10.00, 5000.00, date(2025, 6, 1))
        # Buy more in 2025 at different price
        _add_tx(db, user.id, ac.id, "WEGE3", "buy", 500, 20.00, 10000.00, date(2025, 12, 1))
        # Avg cost = (500*10 + 500*20) / 1000 = 15
        # Sell in 2026 at R$25, 1000 shares (total = R$25,000, gain = 10,000)
        _add_tx(db, user.id, ac.id, "WEGE3", "sell", 1000, 25.00, 25000.00, date(2026, 1, 15))

        service = TaxService(db)
        report = service.get_monthly_report(user.id, 2026)

        jan = report[0]
        assert jan["stocks"]["exempt"] is False
        assert Decimal(jan["stocks"]["total_gain"]) == Decimal("10000.00000000")
        # 15% of 10,000 = 1,500
        assert Decimal(jan["stocks"]["tax_due"]) == Decimal("1500.00")
