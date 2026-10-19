"""Password hashing and JWT helpers used by the authentication flow."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.exc import InvalidHashError
from passlib.hash import pbkdf2_sha256 as passlib_pbkdf2_sha256

from app.core.config import settings


_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 600_000
_PASSWORD_SALT_BYTES = 16
_PASSWORD_HASH_BYTES = 32
_SCRYPT_MAX_MEMORY_BYTES = 128 * 1024 * 1024
_SCRYPT_MAX_WORKING_MEMORY_BYTES = 64 * 1024 * 1024

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
    """Verify current PBKDF2 and supported legacy password hashes."""
    if stored_hash is None:
        return False

    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                stored_hash.encode("ascii"),
            )
        except (TypeError, ValueError, UnicodeEncodeError):
            return False

    if stored_hash.startswith("$pbkdf2-sha256$"):
        try:
            return passlib_pbkdf2_sha256.verify(plain_password, stored_hash)
        except (InvalidHashError, TypeError, ValueError):
            return False

    if stored_hash.startswith("scrypt:"):
        try:
            method, salt_text, digest_text = stored_hash.split("$")
            _, n_text, r_text, p_text = method.split(":")
            n, r, p = int(n_text), int(r_text), int(p_text)
            salt = salt_text.encode("ascii")
            expected_digest = bytes.fromhex(digest_text)
        except (ValueError, TypeError, UnicodeEncodeError):
            return False

        working_memory = 128 * n * r
        if (
            n < 2
            or n & (n - 1)
            or not 1 <= r <= 16
            or not 1 <= p <= 4
            or working_memory > _SCRYPT_MAX_WORKING_MEMORY_BYTES
            or not salt
            or len(salt) > 128
            or not 16 <= len(expected_digest) <= 128
        ):
            return False

        try:
            actual_digest = hashlib.scrypt(
                plain_password.encode("utf-8"),
                salt=salt,
                n=n,
                r=r,
                p=p,
                maxmem=_SCRYPT_MAX_MEMORY_BYTES,
                dklen=len(expected_digest),
            )
        except (ValueError, MemoryError):
            return False
        return hmac.compare_digest(actual_digest, expected_digest)

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


def password_hash_needs_rehash(stored_hash: str) -> bool:
    """Return whether a successfully verified hash uses a legacy format."""
    if stored_hash.startswith(
        ("$2a$", "$2b$", "$2y$", "$pbkdf2-sha256$", "scrypt:")
    ):
        return True

    try:
        scheme, iterations_text, _, _ = stored_hash.split("$")
        iterations = int(iterations_text)
    except (ValueError, TypeError):
        return True

    return scheme != _PASSWORD_SCHEME or iterations != _PASSWORD_ITERATIONS


def password_hash_scheme(stored_hash: str | None) -> str:
    """Return a safe format label without exposing the stored hash."""
    if stored_hash is None:
        return "missing"
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        return "bcrypt"
    if stored_hash.startswith("$pbkdf2-sha256$"):
        return "passlib-pbkdf2-sha256"
    if stored_hash.startswith("scrypt:"):
        return "werkzeug-scrypt"
    if stored_hash.startswith(f"{_PASSWORD_SCHEME}$"):
        return _PASSWORD_SCHEME
    return "unsupported"


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