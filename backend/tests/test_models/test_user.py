import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User


def test_create_user(db):
    user = User(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert len(user.id) == 36
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.created_at is not None
    assert user.updated_at is not None


def test_unique_email_constraint(db):
    u1 = User(name="Alice", email="alice@example.com")
    db.add(u1)
    db.commit()

    u2 = User(name="Bob", email="alice@example.com")
    db.add(u2)
    with pytest.raises(IntegrityError):
        db.commit()
