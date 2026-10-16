"""Password hashing and JWT helpers used by the authentication flow."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings


_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 600_000
_PASSWORD_SALT_BYTES = 16
_PASSWORD_HASH_BYTES = 32

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """Return a salted PBKDF2-SHA256 hash suitable for password storage."""
    salt = secrets.token_bytes(_PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_ITERATIONS,
        dklen=_PASSWORD_HASH_BYTES,
    )
    return f"{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(plain_password: str, stored_hash: str | None) -> bool:
    """Verify a stored password hash, rejecting malformed or unknown formats."""
    if stored_hash is None:
        return False

    try:
        scheme, iterations_text, salt_text, digest_text = stored_hash.split("$")
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_text)
        expected_digest = bytes.fromhex(digest_text)
    except (ValueError, TypeError):
        return False

    if (
        scheme != _PASSWORD_SCHEME
        or not 100_000 <= iterations <= 2_000_000
        or len(salt) != _PASSWORD_SALT_BYTES
        or len(expected_digest) != _PASSWORD_HASH_BYTES
    ):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        iterations,
        dklen=_PASSWORD_HASH_BYTES,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(
    user_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed access token whose subject is the stable user ID."""
    now = datetime.now(UTC)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(seconds=settings.JWT_ACCESS_TOKEN_EXPIRES)
    )
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": expires_at,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int | None:
    """Return the user ID for a valid access token, or None for invalid tokens."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError:
        return None

    subject = payload.get("sub")
    if payload.get("type") != "access" or not isinstance(subject, str):
        return None

    try:
        return int(subject)
    except ValueError:
        return None