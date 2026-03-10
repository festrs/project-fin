from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight


def test_create_asset_weight(db):
    user = User(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="Stocks")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    aw = AssetWeight(asset_class_id=ac.id, symbol="AAPL")
    db.add(aw)
    db.commit()
    db.refresh(aw)

    assert aw.id is not None
    assert len(aw.id) == 36
    assert aw.asset_class_id == ac.id
    assert aw.symbol == "AAPL"
    assert aw.target_weight == 0.0
    assert aw.created_at is not None
    assert aw.updated_at is not None


def test_asset_class_relationship(db):
    user = User(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="Stocks")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    aw1 = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=0.5)
    aw2 = AssetWeight(asset_class_id=ac.id, symbol="GOOGL", target_weight=0.5)
    db.add_all([aw1, aw2])
    db.commit()
    db.refresh(ac)

    assert len(ac.assets) == 2
    symbols = {a.symbol for a in ac.assets}
    assert symbols == {"AAPL", "GOOGL"}
