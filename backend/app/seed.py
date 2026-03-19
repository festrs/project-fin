from sqlalchemy import text, inspect

from app.database import SessionLocal
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.quarantine_config import QuarantineConfig


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


def seed_data():
    db = SessionLocal()
    try:
        _backfill_asset_class_types(db)
        _backfill_stock_split_event_type(db)

        user_count = db.query(User).count()
        if user_count > 0:
            return

        user = User(id="default-user-id", name="Default User", email="default@projectfin.com")
        db.add(user)
        db.flush()

        class_configs = [
            ("US Stocks", "US", "stock"),
            ("BR Stocks", "BR", "stock"),
            ("Crypto", "US", "crypto"),
            ("Stablecoins", "US", "crypto"),
            ("FIIs", "BR", "stock"),
            ("REITs", "US", "stock"),
        ]
        for name, country, type_ in class_configs:
            ac = AssetClass(user_id=user.id, name=name, target_weight=25.0, country=country, type=type_)
            db.add(ac)

        config = QuarantineConfig(user_id=user.id, threshold=2, period_days=180)
        db.add(config)

        db.commit()
    finally:
        db.close()
