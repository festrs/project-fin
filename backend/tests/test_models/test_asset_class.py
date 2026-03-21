from app.models.user import User
from app.models.asset_class import AssetClass
from app.services.auth import hash_password


def test_create_asset_class(db):
    user = User(name="Alice", email="alice@example.com", password_hash=hash_password("testpass"))
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="Stocks")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    assert ac.id is not None
    assert len(ac.id) == 36
    assert ac.user_id == user.id
    assert ac.name == "Stocks"
    assert ac.created_at is not None
    assert ac.updated_at is not None


def test_default_target_weight(db):
    user = User(name="Alice", email="alice@example.com", password_hash=hash_password("testpass"))
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="Bonds")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    assert ac.target_weight == 0.0
