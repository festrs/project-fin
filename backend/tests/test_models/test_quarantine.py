from app.models.user import User
from app.models.quarantine_config import QuarantineConfig
from app.services.auth import hash_password


def test_create_with_defaults(db):
    user = User(name="Alice", email="alice@example.com", password_hash=hash_password("testpass"))
    db.add(user)
    db.commit()
    db.refresh(user)

    qc = QuarantineConfig(user_id=user.id)
    db.add(qc)
    db.commit()
    db.refresh(qc)

    assert qc.id is not None
    assert len(qc.id) == 36
    assert qc.user_id == user.id
    assert qc.threshold == 2
    assert qc.period_days == 180
    assert qc.created_at is not None
    assert qc.updated_at is not None


def test_create_with_custom_values(db):
    user = User(name="Bob", email="bob@example.com", password_hash=hash_password("testpass"))
    db.add(user)
    db.commit()
    db.refresh(user)

    qc = QuarantineConfig(user_id=user.id, threshold=5, period_days=365)
    db.add(qc)
    db.commit()
    db.refresh(qc)

    assert qc.threshold == 5
    assert qc.period_days == 365
