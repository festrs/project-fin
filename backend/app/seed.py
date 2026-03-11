from app.database import SessionLocal
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.quarantine_config import QuarantineConfig


def seed_data():
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            return

        user = User(id="default-user-id", name="Default User", email="default@projectfin.com")
        db.add(user)
        db.flush()

        class_names = ["US Stocks", "BR Stocks", "Crypto", "Stablecoins"]
        for name in class_names:
            ac = AssetClass(user_id=user.id, name=name, target_weight=25.0)
            db.add(ac)

        config = QuarantineConfig(user_id=user.id, threshold=2, period_days=180)
        db.add(config)

        db.commit()
    finally:
        db.close()
