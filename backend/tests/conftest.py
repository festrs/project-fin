import os
os.environ["ENABLE_SCHEDULER"] = "false"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth import hash_password, create_access_token

from fastapi.testclient import TestClient

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def default_user(db):
    user = User(
        name="Default User",
        email="default@example.com",
        password_hash=hash_password("testpass"),
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def auth_headers(default_user):
    token = create_access_token(default_user.id)
    return {"Authorization": f"Bearer {token}"}
