import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


def test_hash_and_verify_password():
    plain = "super_secret_123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong_password", hashed)


def test_create_and_decode_token():
    subject = "user-uuid-123"
    token = create_access_token(subject=subject)
    payload = decode_token(token)
    assert payload["sub"] == subject


def test_invalid_token_raises():
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_token("not.a.real.token")
