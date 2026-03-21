import pytest
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token("user-123")
    assert isinstance(token, str)
    user_id = decode_access_token(token)
    assert user_id == "user-123"


def test_decode_access_token_invalid():
    with pytest.raises(Exception):
        decode_access_token("invalid.token.here")


def test_decode_access_token_expired():
    import jwt as pyjwt
    from datetime import datetime, timedelta
    from app.config import settings

    # Create a token that expired in the past
    past = datetime.utcnow() - timedelta(days=1)
    payload = {"sub": "user-123", "exp": past}
    token = pyjwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    with pytest.raises(Exception):
        decode_access_token(token)
