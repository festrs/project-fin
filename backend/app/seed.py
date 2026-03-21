import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text, inspect

from app.database import SessionLocal
from app.models.user import User
from app.services.auth import hash_password
from app.config import settings
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.models.quarantine_config import QuarantineConfig

logger = logging.getLogger(__name__)

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "portfolio_seed.json"


def _backfill_asset_class_types(db):
    """Ensure type column exists and backfill based on name keywords."""
    inspector = inspect(db.bind)
    columns = [c["name"] for c in inspector.get_columns("asset_classes")]
    if "type" not in columns:
        db.execute(text("ALTER TABLE asset_classes ADD COLUMN type VARCHAR(20) NOT NULL DEFAULT 'stock'"))
        db.commit()

    crypto_names = {"Crypto", "Cryptos", "Criptomoedas"}
    classes = db.query(AssetClass).filter(AssetClass.type == "stock").all()
    for ac in classes:
        if ac.name in crypto_names or ac.name == "Stablecoins":
            ac.type = "crypto"
        elif any(term in ac.name.lower() for term in ["renda fixa", "fixed income"]):
            ac.type = "fixed_income"
    db.commit()


def _backfill_stock_split_event_type(db):
    """Ensure event_type column exists on stock_splits."""
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    if "stock_splits" not in tables:
        return
    columns = [c["name"] for c in inspector.get_columns("stock_splits")]
    if "event_type" not in columns:
        db.execute(text("ALTER TABLE stock_splits ADD COLUMN event_type VARCHAR(20) NOT NULL DEFAULT 'split'"))
        db.commit()


def _seed_from_json(db):
    """Seed full portfolio from JSON file."""
    if not SEED_FILE.exists():
        logger.warning("Seed file not found: %s", SEED_FILE)
        return

    with open(SEED_FILE) as f:
        data = json.load(f)

    user_data = data["user"]
    user = User(
        id=user_data["id"],
        name=user_data["name"],
        email=user_data["email"],
        password_hash=hash_password(settings.default_user_password),
    )
    db.add(user)
    db.flush()

    class_map = {}
    for ac_data in data["asset_classes"]:
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

    for class_name, holdings in data["holdings"].items():
        ac = class_map.get(class_name)
        if not ac:
            continue
        for h in holdings:
            unit_price = Decimal(h["unit_price"])
            quantity = h["quantity"]
            total_value = (unit_price * Decimal(str(quantity))).quantize(Decimal("0.01"))

            db.add(AssetWeight(
                asset_class_id=ac.id,
                symbol=h["symbol"],
                target_weight=h.get("target_weight", 0.0),
            ))
            db.add(Transaction(
                user_id=user.id,
                asset_class_id=ac.id,
                asset_symbol=h["symbol"],
                type="buy",
                quantity=quantity,
                unit_price=unit_price,
                total_value=total_value,
                currency=h["currency"],
                tax_amount=Decimal("0"),
                date=date(2024, 1, 1),
                notes="Imported from Investimentos.numbers",
            ))

    for qc_data in data.get("quarantine_configs", []):
        db.add(QuarantineConfig(
            user_id=user.id,
            threshold=qc_data["threshold"],
            period_days=qc_data["period_days"],
        ))

    db.commit()
    logger.info("Seeded portfolio from %s", SEED_FILE)


def seed_data():
    db = SessionLocal()
    try:
        _backfill_asset_class_types(db)
        _backfill_stock_split_event_type(db)

        user_count = db.query(User).count()
        if user_count > 0:
            return

        _seed_from_json(db)
    finally:
        db.close()
