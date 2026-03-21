"""
Import portfolio data from data/portfolio_seed.json into the database.

Usage:
    cd backend && python -m scripts.import_portfolio          # Uses default DB from config
    cd backend && python -m scripts.import_portfolio --reset   # Wipe and re-import
"""
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add parent to path so app imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.models.quarantine_config import QuarantineConfig


SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "portfolio_seed.json"


def import_portfolio(reset: bool = False):
    if not SEED_FILE.exists():
        print(f"Seed file not found: {SEED_FILE}")
        return

    with open(SEED_FILE) as f:
        data = json.load(f)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if reset:
            print("Resetting database...")
            db.query(Transaction).delete()
            db.query(AssetWeight).delete()
            db.query(QuarantineConfig).delete()
            db.query(AssetClass).delete()
            db.query(User).delete()
            db.commit()
            print("  All data cleared.")

        # 1. User
        user_data = data["user"]
        user = db.query(User).filter(User.id == user_data["id"]).first()
        if not user:
            user = User(id=user_data["id"], name=user_data["name"], email=user_data["email"])
            db.add(user)
            db.flush()
            print(f"Created user: {user.name}")
        else:
            print(f"User already exists: {user.name}")

        # 2. Asset classes
        class_map = {}  # name -> AssetClass
        for ac_data in data["asset_classes"]:
            existing = db.query(AssetClass).filter(
                AssetClass.user_id == user.id,
                AssetClass.name == ac_data["name"],
            ).first()
            if existing:
                existing.target_weight = ac_data["target_weight"]
                existing.country = ac_data["country"]
                existing.type = ac_data["type"]
                class_map[ac_data["name"]] = existing
                print(f"  Updated asset class: {ac_data['name']}")
            else:
                ac = AssetClass(
                    user_id=user.id,
                    name=ac_data["name"],
                    target_weight=ac_data["target_weight"],
                    country=ac_data["country"],
                    type=ac_data["type"],
                )
                db.add(ac)
                db.flush()
                class_map[ac_data["name"]] = ac
                print(f"  Created asset class: {ac_data['name']}")

        db.commit()

        # 3. Holdings -> asset_weights + transactions
        tx_count = 0
        aw_count = 0
        for class_name, holdings in data["holdings"].items():
            ac = class_map.get(class_name)
            if not ac:
                print(f"  WARNING: Asset class '{class_name}' not found, skipping")
                continue

            for h in holdings:
                symbol = h["symbol"]
                quantity = h["quantity"]
                unit_price = Decimal(h["unit_price"])
                total_value = (unit_price * Decimal(str(quantity))).quantize(Decimal("0.01"))
                currency = h["currency"]
                target_weight = h.get("target_weight", 0.0)

                # Asset weight
                existing_aw = db.query(AssetWeight).filter(
                    AssetWeight.asset_class_id == ac.id,
                    AssetWeight.symbol == symbol,
                ).first()
                if existing_aw:
                    existing_aw.target_weight = target_weight
                else:
                    aw = AssetWeight(
                        asset_class_id=ac.id,
                        symbol=symbol,
                        target_weight=target_weight,
                    )
                    db.add(aw)
                    aw_count += 1

                # Transaction (buy)
                existing_tx = db.query(Transaction).filter(
                    Transaction.user_id == user.id,
                    Transaction.asset_symbol == symbol,
                    Transaction.asset_class_id == ac.id,
                ).first()
                if existing_tx:
                    existing_tx.quantity = quantity
                    existing_tx.unit_price = unit_price
                    existing_tx.total_value = total_value
                    existing_tx.currency = currency
                else:
                    tx = Transaction(
                        user_id=user.id,
                        asset_class_id=ac.id,
                        asset_symbol=symbol,
                        type="buy",
                        quantity=quantity,
                        unit_price=unit_price,
                        total_value=total_value,
                        currency=currency,
                        tax_amount=Decimal("0"),
                        date=date(2024, 1, 1),
                        notes="Imported from Investimentos.numbers",
                    )
                    db.add(tx)
                    tx_count += 1

        # 4. Quarantine configs
        for qc_data in data.get("quarantine_configs", []):
            existing_qc = db.query(QuarantineConfig).filter(
                QuarantineConfig.user_id == user.id,
            ).first()
            if not existing_qc:
                qc = QuarantineConfig(
                    user_id=user.id,
                    threshold=qc_data["threshold"],
                    period_days=qc_data["period_days"],
                )
                db.add(qc)

        db.commit()
        print(f"\nImport complete: {tx_count} transactions, {aw_count} asset weights created.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    import_portfolio(reset=reset)
