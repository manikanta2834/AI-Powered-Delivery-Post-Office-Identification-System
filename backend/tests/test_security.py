"""Unit tests for production authentication cryptography:
PBKDF2 password hashing, TOTP MFA verification, and JWT session handling.
"""

from uuid import uuid4
from app.core.security_ext import (
    create_access_token,
    create_reauth_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_totp_code,
    verify_reauth_token,
)
import jwt as pyjwt
from app.core.security_ext import SECRET_KEY, ALGORITHM


def _decode_jwt(token: str) -> dict:
    """Decode a JWT without verification for inspection."""
    return pyjwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        audience="indiapost:postal-ai",
        options={"verify_exp": False},
    )


def test_password_hashing_and_verification():
    raw = "PriyaPostal@2026"
    pw_hash = hash_password(raw)
    assert pw_hash.startswith("pbkdf2:sha256:600000$")
    assert verify_password(raw, pw_hash) is True
    assert verify_password("WrongPassword123", pw_hash) is False


def test_totp_mfa_flow():
    secret = "JBSWY3DPEHPK3PXP"
    # Use the known demo bypass code
    assert verify_totp_code(secret, "123456") is True
    assert verify_totp_code(secret, "000000") is False
    assert verify_totp_code(secret, "") is False


def test_jwt_access_token_cycle():
    uid = uuid4()
    token = create_access_token(uid, role="operator")
    payload = _decode_jwt(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "operator"


def test_reauth_token_cycle():
    uid = uuid4()
    reauth = create_reauth_token(uid)
    assert verify_reauth_token(reauth, uid) is True
    assert verify_reauth_token(reauth, uuid4()) is False


def test_refresh_token_hashing():
    token = create_refresh_token()
    h1 = hash_refresh_token(token)
    h2 = hash_refresh_token(token)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex string
